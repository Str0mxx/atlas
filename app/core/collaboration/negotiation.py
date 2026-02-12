"""ATLAS Agent muzakere modulu.

Contract Net Protocol (CNP) ile gorev tahsisi,
teklif degerlendirme ve kazanan secimi.
"""

import logging
from typing import Any

from app.models.collaboration import (
    AgentMessage,
    Bid,
    BidStatus,
    MessageType,
    Negotiation,
    NegotiationState,
)

logger = logging.getLogger(__name__)


class NegotiationManager:
    """Contract Net Protocol muzakere yoneticisi.

    CFP (Call for Proposal) yayinlama, teklif toplama,
    degerlendirme ve kazanan secimi.

    Attributes:
        negotiations: Aktif muzakereler (id -> Negotiation).
        agent_capabilities: Agent yetenekleri (agent_adi -> [yetenek]).
    """

    def __init__(self) -> None:
        self.negotiations: dict[str, Negotiation] = {}
        self.agent_capabilities: dict[str, list[str]] = {}

    def register_capabilities(
        self, agent_name: str, capabilities: list[str]
    ) -> None:
        """Agent yeteneklerini kayit eder.

        Args:
            agent_name: Agent adi.
            capabilities: Yetenek listesi.
        """
        self.agent_capabilities[agent_name] = list(capabilities)
        logger.debug(
            "Yetenekler kaydedildi: %s -> %s", agent_name, capabilities,
        )

    async def create_cfp(
        self,
        initiator: str,
        task_description: str,
        required_capabilities: list[str] | None = None,
        criteria: dict[str, float] | None = None,
        deadline: float = 30.0,
    ) -> Negotiation:
        """Call for Proposal (CFP) olusturur.

        Args:
            initiator: Baslatan agent adi.
            task_description: Gorev aciklamasi.
            required_capabilities: Gerekli yetenekler.
            criteria: Degerlendirme kriterleri (anahtar -> agirlik).
            deadline: Teklif toplama suresi (saniye).

        Returns:
            Olusturulan muzakere.
        """
        negotiation = Negotiation(
            task_description=task_description,
            initiator=initiator,
            state=NegotiationState.BIDDING,
            deadline=deadline,
        )
        if criteria:
            negotiation.criteria = criteria

        self.negotiations[negotiation.id] = negotiation

        logger.info(
            "CFP olusturuldu: %s (baslatan=%s)",
            negotiation.id,
            initiator,
        )
        return negotiation

    def get_eligible_agents(
        self, required_capabilities: list[str] | None = None
    ) -> list[str]:
        """Gereksinimleri karsilayan agentlari dondurur.

        Args:
            required_capabilities: Gerekli yetenekler.

        Returns:
            Uygun agent listesi.
        """
        if not required_capabilities:
            return list(self.agent_capabilities.keys())

        eligible: list[str] = []
        required_set = set(required_capabilities)
        for agent_name, caps in self.agent_capabilities.items():
            if required_set.issubset(set(caps)):
                eligible.append(agent_name)
        return eligible

    async def submit_bid(
        self,
        negotiation_id: str,
        agent_name: str,
        price: float = 0.0,
        capability_score: float = 0.5,
        estimated_duration: float = 0.0,
        proposal: dict[str, Any] | None = None,
    ) -> Bid | None:
        """Teklif sunar.

        Args:
            negotiation_id: Muzakere ID.
            agent_name: Teklif veren agent.
            price: Maliyet teklifi.
            capability_score: Yetenek puani.
            estimated_duration: Tahmini sure.
            proposal: Detayli teklif.

        Returns:
            Olusturulan teklif veya None (muzakere bulunamadiysa).
        """
        negotiation = self.negotiations.get(negotiation_id)
        if negotiation is None:
            logger.warning("Muzakere bulunamadi: %s", negotiation_id)
            return None

        if negotiation.state != NegotiationState.BIDDING:
            logger.warning(
                "Muzakere teklif kabul etmiyor: %s (durum=%s)",
                negotiation_id,
                negotiation.state.value,
            )
            return None

        bid = Bid(
            agent_name=agent_name,
            negotiation_id=negotiation_id,
            price=price,
            capability_score=capability_score,
            estimated_duration=estimated_duration,
            proposal=proposal or {},
        )
        negotiation.bids.append(bid)

        logger.info(
            "Teklif sunuldu: %s -> muzakere %s (puan=%.2f, fiyat=%.2f)",
            agent_name,
            negotiation_id,
            capability_score,
            price,
        )
        return bid

    async def evaluate_bids(self, negotiation_id: str) -> str | None:
        """Teklifleri degerlendirir ve kazanani secer.

        Agirlikli puanlama: her kriter normalize edilir ve
        agirligiyla carpilarak toplam puan hesaplanir.

        Args:
            negotiation_id: Muzakere ID.

        Returns:
            Kazanan agent adi veya None.
        """
        negotiation = self.negotiations.get(negotiation_id)
        if negotiation is None:
            return None

        pending_bids = [
            b for b in negotiation.bids if b.status == BidStatus.PENDING
        ]
        if not pending_bids:
            negotiation.state = NegotiationState.FAILED
            return None

        criteria = negotiation.criteria
        best_score = -1.0
        best_bid: Bid | None = None

        # Normalizasyon icin min/max hesapla
        max_price = max(b.price for b in pending_bids) or 1.0
        max_duration = max(b.estimated_duration for b in pending_bids) or 1.0

        for bid in pending_bids:
            score = 0.0

            # capability_score: yuksek = iyi
            cap_weight = criteria.get("capability_score", 0.5)
            score += cap_weight * bid.capability_score

            # price: dusuk = iyi (ters normalize)
            price_weight = criteria.get("price", 0.3)
            price_norm = 1.0 - (bid.price / max_price) if max_price > 0 else 1.0
            score += price_weight * price_norm

            # estimated_duration: dusuk = iyi (ters normalize)
            dur_weight = criteria.get("estimated_duration", 0.2)
            dur_norm = 1.0 - (bid.estimated_duration / max_duration) if max_duration > 0 else 1.0
            score += dur_weight * dur_norm

            if score > best_score:
                best_score = score
                best_bid = bid

        if best_bid is None:
            negotiation.state = NegotiationState.FAILED
            return None

        # Kazanani isle
        best_bid.status = BidStatus.ACCEPTED
        for bid in pending_bids:
            if bid.id != best_bid.id:
                bid.status = BidStatus.REJECTED

        negotiation.winner = best_bid.agent_name
        negotiation.state = NegotiationState.AWARDED

        logger.info(
            "Muzakere kazanani: %s -> %s (puan=%.3f)",
            negotiation_id,
            best_bid.agent_name,
            best_score,
        )
        return best_bid.agent_name

    async def complete_negotiation(self, negotiation_id: str) -> bool:
        """Muzakereyi tamamlar.

        Args:
            negotiation_id: Muzakere ID.

        Returns:
            Basarili mi.
        """
        negotiation = self.negotiations.get(negotiation_id)
        if negotiation is None:
            return False

        if negotiation.state == NegotiationState.AWARDED:
            negotiation.state = NegotiationState.COMPLETED
            return True

        return False

    async def cancel_negotiation(self, negotiation_id: str) -> bool:
        """Muzakereyi iptal eder.

        Args:
            negotiation_id: Muzakere ID.

        Returns:
            Basarili mi.
        """
        negotiation = self.negotiations.get(negotiation_id)
        if negotiation is None:
            return False

        if negotiation.state in (
            NegotiationState.COMPLETED,
            NegotiationState.CANCELLED,
        ):
            return False

        negotiation.state = NegotiationState.CANCELLED
        for bid in negotiation.bids:
            if bid.status == BidStatus.PENDING:
                bid.status = BidStatus.WITHDRAWN
        return True

    def get_agent_wins(self, agent_name: str) -> int:
        """Agent'in kazandigi muzakere sayisini dondurur.

        Args:
            agent_name: Agent adi.

        Returns:
            Kazanma sayisi.
        """
        return sum(
            1
            for n in self.negotiations.values()
            if n.winner == agent_name
            and n.state in (NegotiationState.AWARDED, NegotiationState.COMPLETED)
        )

    def get_active_negotiations(self) -> list[Negotiation]:
        """Aktif muzakereleri dondurur.

        Returns:
            Aktif muzakere listesi.
        """
        return [
            n
            for n in self.negotiations.values()
            if n.state in (NegotiationState.OPEN, NegotiationState.BIDDING)
        ]
