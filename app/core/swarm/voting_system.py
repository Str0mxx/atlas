"""ATLAS Oylama Sistemi modulu.

Demokratik karar alma, agirlikli oylama,
yeter sayi kurallari, veto hakki ve konsensus.
"""

import logging
from typing import Any

from app.models.swarm import VoteSession, VoteType

logger = logging.getLogger(__name__)


class VotingSystem:
    """Oylama sistemi.

    Suru uyelerinin kolektif karar almasini saglar.
    Farkli oylama yontemlerini destekler.

    Attributes:
        _sessions: Oylama oturumlari.
        _veto_holders: Veto hakki olan agent'lar.
        _default_threshold: Varsayilan kazanma esigi.
    """

    def __init__(
        self,
        default_threshold: float = 0.5,
    ) -> None:
        """Oylama sistemini baslatir.

        Args:
            default_threshold: Varsayilan kazanma esigi.
        """
        self._sessions: dict[str, VoteSession] = {}
        self._veto_holders: set[str] = set()
        self._default_threshold = default_threshold

        logger.info("VotingSystem baslatildi (threshold=%.2f)", default_threshold)

    def create_session(
        self,
        topic: str,
        options: list[str],
        vote_type: VoteType = VoteType.MAJORITY,
        quorum: int = 0,
        weights: dict[str, float] | None = None,
    ) -> VoteSession:
        """Oylama oturumu olusturur.

        Args:
            topic: Konu.
            options: Secenekler.
            vote_type: Oylama tipi.
            quorum: Yeter sayi.
            weights: Agent agirliklari.

        Returns:
            VoteSession nesnesi.
        """
        session = VoteSession(
            topic=topic,
            options=options,
            vote_type=vote_type,
            quorum=quorum,
            weights=weights or {},
        )
        self._sessions[session.session_id] = session

        logger.info("Oylama oturumu: %s (%s)", topic, vote_type.value)
        return session

    def cast_vote(
        self,
        session_id: str,
        agent_id: str,
        choice: str,
    ) -> bool:
        """Oy kullanir.

        Args:
            session_id: Oturum ID.
            agent_id: Agent ID.
            choice: Secim.

        Returns:
            Basarili ise True.
        """
        session = self._sessions.get(session_id)
        if not session or session.resolved:
            return False

        if not choice.startswith("VETO:") and choice not in session.options:
            return False

        session.votes[agent_id] = choice
        return True

    def resolve(self, session_id: str) -> str:
        """Oylama sonucunu belirler.

        Args:
            session_id: Oturum ID.

        Returns:
            Kazanan secenek veya bos string.
        """
        session = self._sessions.get(session_id)
        if not session or session.resolved:
            return session.winner if session else ""

        # Yeter sayi kontrolu
        if session.quorum > 0 and len(session.votes) < session.quorum:
            return ""

        # Veto kontrolu
        for agent_id in self._veto_holders:
            if agent_id in session.votes:
                vote = session.votes[agent_id]
                if vote.startswith("VETO:"):
                    session.resolved = True
                    session.winner = ""
                    return ""

        winner = ""
        if session.vote_type == VoteType.MAJORITY:
            winner = self._resolve_majority(session)
        elif session.vote_type == VoteType.UNANIMOUS:
            winner = self._resolve_unanimous(session)
        elif session.vote_type == VoteType.WEIGHTED:
            winner = self._resolve_weighted(session)
        elif session.vote_type == VoteType.QUORUM:
            winner = self._resolve_majority(session)

        session.resolved = True
        session.winner = winner
        return winner

    def grant_veto(self, agent_id: str) -> None:
        """Veto hakki verir.

        Args:
            agent_id: Agent ID.
        """
        self._veto_holders.add(agent_id)

    def revoke_veto(self, agent_id: str) -> None:
        """Veto hakkini alir.

        Args:
            agent_id: Agent ID.
        """
        self._veto_holders.discard(agent_id)

    def get_session(self, session_id: str) -> VoteSession | None:
        """Oturumu getirir.

        Args:
            session_id: Oturum ID.

        Returns:
            VoteSession veya None.
        """
        return self._sessions.get(session_id)

    def get_results(self, session_id: str) -> dict[str, Any]:
        """Oylama sonuclarini getirir.

        Args:
            session_id: Oturum ID.

        Returns:
            Sonuc sozlugu.
        """
        session = self._sessions.get(session_id)
        if not session:
            return {}

        # Oy sayimi
        counts: dict[str, int] = {}
        for choice in session.votes.values():
            counts[choice] = counts.get(choice, 0) + 1

        return {
            "topic": session.topic,
            "vote_type": session.vote_type.value,
            "total_votes": len(session.votes),
            "counts": counts,
            "resolved": session.resolved,
            "winner": session.winner,
        }

    def _resolve_majority(self, session: VoteSession) -> str:
        """Cogunluk ile cozer."""
        counts: dict[str, int] = {}
        for choice in session.votes.values():
            counts[choice] = counts.get(choice, 0) + 1

        if not counts:
            return ""

        total = len(session.votes)
        winner = max(counts, key=counts.get)

        if counts[winner] / total >= self._default_threshold:
            return winner
        return ""

    def _resolve_unanimous(self, session: VoteSession) -> str:
        """Oybirligi ile cozer."""
        if not session.votes:
            return ""

        choices = set(session.votes.values())
        if len(choices) == 1:
            return choices.pop()
        return ""

    def _resolve_weighted(self, session: VoteSession) -> str:
        """Agirlikli oylama ile cozer."""
        weighted_counts: dict[str, float] = {}

        for agent_id, choice in session.votes.items():
            weight = session.weights.get(agent_id, 1.0)
            weighted_counts[choice] = weighted_counts.get(choice, 0.0) + weight

        if not weighted_counts:
            return ""

        return max(weighted_counts, key=weighted_counts.get)

    @property
    def total_sessions(self) -> int:
        """Toplam oturum sayisi."""
        return len(self._sessions)

    @property
    def active_sessions(self) -> int:
        """Aktif oturum sayisi."""
        return sum(1 for s in self._sessions.values() if not s.resolved)

    @property
    def veto_holder_count(self) -> int:
        """Veto hakki olan agent sayisi."""
        return len(self._veto_holders)
