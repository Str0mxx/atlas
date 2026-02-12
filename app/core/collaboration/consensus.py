"""ATLAS Agent konsensus modulu.

Cogunluk, oybirliği, agirlikli oylama ve yeter sayili
konsensus mekanizmalari.
"""

import logging
from typing import Any

from app.models.collaboration import (
    ConsensusMethod,
    ConsensusSession,
    Vote,
    VoteType,
)

logger = logging.getLogger(__name__)


class ConsensusBuilder:
    """Konsensus olusturucu.

    Agentlar arasi oylama, agirlikli konsensus ve
    catisma cozumu.

    Attributes:
        sessions: Oylama oturumlari (id -> ConsensusSession).
        agent_weights: Agent oy agirliklari (agent_adi -> agirlik).
    """

    def __init__(self) -> None:
        self.sessions: dict[str, ConsensusSession] = {}
        self.agent_weights: dict[str, float] = {}

    def set_agent_weight(self, agent_name: str, weight: float) -> None:
        """Agent oy agirligini ayarlar.

        Args:
            agent_name: Agent adi.
            weight: Agirlik (>= 0).
        """
        self.agent_weights[agent_name] = max(0.0, weight)

    async def create_session(
        self,
        topic: str,
        method: ConsensusMethod = ConsensusMethod.MAJORITY,
        quorum: float = 0.5,
    ) -> ConsensusSession:
        """Yeni oylama oturumu olusturur.

        Args:
            topic: Oylama konusu.
            method: Konsensus yontemi.
            quorum: Yeter sayi orani (0.0-1.0).

        Returns:
            Olusturulan oturum.
        """
        session = ConsensusSession(
            topic=topic,
            method=method,
            quorum=quorum,
        )
        self.sessions[session.id] = session

        logger.info(
            "Konsensus oturumu olusturuldu: %s (yontem=%s, konu=%s)",
            session.id,
            method.value,
            topic,
        )
        return session

    async def cast_vote(
        self,
        session_id: str,
        agent_name: str,
        vote_type: VoteType,
        reason: str = "",
    ) -> Vote | None:
        """Oy kullanir.

        Args:
            session_id: Oturum ID.
            agent_name: Oy kullanan agent.
            vote_type: Oy tipi.
            reason: Oy gerekçesi.

        Returns:
            Oy kaydi veya None.
        """
        session = self.sessions.get(session_id)
        if session is None:
            return None

        if session.resolved:
            logger.warning("Oturum zaten sonuclanmis: %s", session_id)
            return None

        # Ayni agent tekrar oy kullanamasin
        for existing in session.votes:
            if existing.agent_name == agent_name:
                logger.warning("Agent zaten oy kullanmis: %s", agent_name)
                return None

        weight = self.agent_weights.get(agent_name, 1.0)
        vote = Vote(
            agent_name=agent_name,
            vote_type=vote_type,
            weight=weight,
            reason=reason,
        )
        session.votes.append(vote)

        logger.debug(
            "Oy kullanildi: %s -> %s (agirlik=%.1f)",
            agent_name,
            vote_type.value,
            weight,
        )
        return vote

    async def resolve(
        self,
        session_id: str,
        total_agents: int | None = None,
    ) -> VoteType | None:
        """Oylama sonucunu belirler.

        Args:
            session_id: Oturum ID.
            total_agents: Toplam oy kullanabilecek agent sayisi (quorum icin).

        Returns:
            Sonuc (APPROVE/REJECT) veya None (cozulemezse).
        """
        session = self.sessions.get(session_id)
        if session is None:
            return None

        if session.resolved:
            return session.result

        votes = session.votes
        if not votes:
            return None

        # Quorum kontrolu
        if total_agents and total_agents > 0:
            participation = len(votes) / total_agents
            if participation < session.quorum:
                logger.warning(
                    "Yeter sayi saglanamadi: %.1f%% < %.1f%%",
                    participation * 100,
                    session.quorum * 100,
                )
                return None

        result: VoteType | None = None

        if session.method == ConsensusMethod.MAJORITY:
            result = self._resolve_majority(votes)
        elif session.method == ConsensusMethod.UNANIMOUS:
            result = self._resolve_unanimous(votes)
        elif session.method == ConsensusMethod.WEIGHTED:
            result = self._resolve_weighted(votes)
        elif session.method == ConsensusMethod.QUORUM:
            result = self._resolve_quorum(votes, session.quorum)

        if result is not None:
            session.resolved = True
            session.result = result
            logger.info(
                "Konsensus sonucu: %s -> %s", session_id, result.value,
            )

        return result

    def _resolve_majority(self, votes: list[Vote]) -> VoteType:
        """Basit cogunluk ile cozum.

        Args:
            votes: Oy listesi.

        Returns:
            Cogunluk oyu.
        """
        approve = sum(1 for v in votes if v.vote_type == VoteType.APPROVE)
        reject = sum(1 for v in votes if v.vote_type == VoteType.REJECT)

        if approve > reject:
            return VoteType.APPROVE
        elif reject > approve:
            return VoteType.REJECT
        else:
            return VoteType.ABSTAIN

    def _resolve_unanimous(self, votes: list[Vote]) -> VoteType:
        """Oybirligi ile cozum.

        Args:
            votes: Oy listesi.

        Returns:
            APPROVE (hepsi onayladiysa) veya REJECT.
        """
        non_abstain = [v for v in votes if v.vote_type != VoteType.ABSTAIN]
        if not non_abstain:
            return VoteType.ABSTAIN

        all_approve = all(v.vote_type == VoteType.APPROVE for v in non_abstain)
        return VoteType.APPROVE if all_approve else VoteType.REJECT

    def _resolve_weighted(self, votes: list[Vote]) -> VoteType:
        """Agirlikli oylama ile cozum.

        Args:
            votes: Oy listesi.

        Returns:
            Agirlikli cogunluk oyu.
        """
        approve_weight = sum(
            v.weight for v in votes if v.vote_type == VoteType.APPROVE
        )
        reject_weight = sum(
            v.weight for v in votes if v.vote_type == VoteType.REJECT
        )

        if approve_weight > reject_weight:
            return VoteType.APPROVE
        elif reject_weight > approve_weight:
            return VoteType.REJECT
        else:
            return VoteType.ABSTAIN

    def _resolve_quorum(
        self, votes: list[Vote], quorum: float
    ) -> VoteType:
        """Yeter sayili cozum.

        Onay orani >= quorum ise APPROVE.

        Args:
            votes: Oy listesi.
            quorum: Yeter sayi orani.

        Returns:
            Sonuc.
        """
        non_abstain = [v for v in votes if v.vote_type != VoteType.ABSTAIN]
        if not non_abstain:
            return VoteType.ABSTAIN

        approve_count = sum(
            1 for v in non_abstain if v.vote_type == VoteType.APPROVE
        )
        approve_ratio = approve_count / len(non_abstain)

        if approve_ratio >= quorum:
            return VoteType.APPROVE
        else:
            return VoteType.REJECT

    def get_session_summary(
        self, session_id: str
    ) -> dict[str, Any] | None:
        """Oturum ozetini dondurur.

        Args:
            session_id: Oturum ID.

        Returns:
            Ozet sozlugu veya None.
        """
        session = self.sessions.get(session_id)
        if session is None:
            return None

        approve = sum(1 for v in session.votes if v.vote_type == VoteType.APPROVE)
        reject = sum(1 for v in session.votes if v.vote_type == VoteType.REJECT)
        abstain = sum(1 for v in session.votes if v.vote_type == VoteType.ABSTAIN)

        return {
            "topic": session.topic,
            "method": session.method.value,
            "total_votes": len(session.votes),
            "approve": approve,
            "reject": reject,
            "abstain": abstain,
            "resolved": session.resolved,
            "result": session.result.value if session.result else None,
        }
