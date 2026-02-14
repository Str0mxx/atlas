"""ATLAS Suru Orkestratoru modulu.

Tam suru yonetimi, gorev atama, performans izleme,
adaptif optimizasyon ve hiyerarsi entegrasyonu.
"""

import logging
from typing import Any

from app.models.swarm import (
    AuctionState,
    PheromoneType,
    SwarmSnapshot,
    SwarmState,
    VoteType,
)

from app.core.swarm.collective_memory import CollectiveMemory
from app.core.swarm.emergent_behavior import EmergentBehavior
from app.core.swarm.fault_tolerance import SwarmFaultTolerance
from app.core.swarm.load_balancer import SwarmLoadBalancer
from app.core.swarm.pheromone_system import PheromoneSystem
from app.core.swarm.swarm_coordinator import SwarmCoordinator
from app.core.swarm.task_auction import TaskAuction
from app.core.swarm.voting_system import VotingSystem

logger = logging.getLogger(__name__)


class SwarmOrchestrator:
    """Suru orkestratoru.

    Tum suru alt sistemlerini koordine eder,
    tam yasam dongusu yonetimi saglar.

    Attributes:
        _coordinator: Suru koordinatoru.
        _pheromones: Feromon sistemi.
        _memory: Kolektif hafiza.
        _voting: Oylama sistemi.
        _auction: Gorev acik artirma.
        _emergent: Ortaya cikan davranis.
        _balancer: Yuk dengeleyici.
        _fault: Hata toleransi.
    """

    def __init__(
        self,
        min_swarm_size: int = 2,
        max_swarm_size: int = 20,
        voting_threshold: float = 0.5,
        pheromone_decay_rate: float = 0.1,
    ) -> None:
        """Orkestratoru baslatir.

        Args:
            min_swarm_size: Min suru boyutu.
            max_swarm_size: Maks suru boyutu.
            voting_threshold: Oylama esigi.
            pheromone_decay_rate: Feromon bozunma orani.
        """
        self._coordinator = SwarmCoordinator(min_swarm_size, max_swarm_size)
        self._pheromones = PheromoneSystem(decay_rate=pheromone_decay_rate)
        self._memory = CollectiveMemory()
        self._voting = VotingSystem(default_threshold=voting_threshold)
        self._auction = TaskAuction()
        self._emergent = EmergentBehavior()
        self._balancer = SwarmLoadBalancer()
        self._fault = SwarmFaultTolerance()

        logger.info(
            "SwarmOrchestrator baslatildi "
            "(min=%d, max=%d, vote=%.2f, decay=%.2f)",
            min_swarm_size, max_swarm_size,
            voting_threshold, pheromone_decay_rate,
        )

    def create_mission(
        self,
        name: str,
        goal: str,
        agent_ids: list[str],
    ) -> dict[str, Any]:
        """Gorev surusi olusturur.

        Args:
            name: Suru adi.
            goal: Hedef.
            agent_ids: Katilacak agent'lar.

        Returns:
            Olusturma sonucu.
        """
        swarm = self._coordinator.create_swarm(name=name, goal=goal)

        joined = 0
        for agent_id in agent_ids:
            if self._coordinator.join_swarm(swarm.swarm_id, agent_id):
                self._balancer.register_agent(agent_id)
                self._fault.register_agent(agent_id)
                self._auction.register_agent(agent_id, [])
                joined += 1

        # Hedef belirle
        if joined >= swarm.min_size:
            self._coordinator.set_goal(swarm.swarm_id, goal)

        return {
            "success": True,
            "swarm_id": swarm.swarm_id,
            "name": name,
            "members": joined,
            "state": swarm.state.value,
        }

    def assign_task(
        self,
        swarm_id: str,
        task_id: str,
        description: str = "",
        use_auction: bool = False,
        required_capabilities: list[str] | None = None,
    ) -> dict[str, Any]:
        """Suruye gorev atar.

        Args:
            swarm_id: Suru ID.
            task_id: Gorev ID.
            description: Aciklama.
            use_auction: Acik artirma kullan.
            required_capabilities: Gereken yetenekler.

        Returns:
            Atama sonucu.
        """
        swarm = self._coordinator.get_swarm(swarm_id)
        if not swarm:
            return {"success": False, "reason": "Suru bulunamadi"}

        if use_auction:
            auction = self._auction.create_auction(
                task_id, description, required_capabilities,
            )
            return {
                "success": True,
                "method": "auction",
                "auction_id": auction.auction_id,
            }

        # Yuk dengeleyici ile ata
        assigned = self._balancer.assign_task(task_id)
        if not assigned:
            return {"success": False, "reason": "Uygun agent yok"}

        # Feromon birak
        self._pheromones.leave_marker(
            assigned, f"task:{task_id}",
            PheromoneType.TRAIL, 0.8,
            {"task_id": task_id},
        )

        return {
            "success": True,
            "method": "load_balance",
            "agent_id": assigned,
        }

    def vote_on_decision(
        self,
        swarm_id: str,
        topic: str,
        options: list[str],
        votes: dict[str, str],
        vote_type: VoteType = VoteType.MAJORITY,
    ) -> dict[str, Any]:
        """Suru oylama yapar.

        Args:
            swarm_id: Suru ID.
            topic: Konu.
            options: Secenekler.
            votes: Agent -> secim.
            vote_type: Oylama tipi.

        Returns:
            Oylama sonucu.
        """
        session = self._voting.create_session(topic, options, vote_type)

        for agent_id, choice in votes.items():
            self._voting.cast_vote(session.session_id, agent_id, choice)

        winner = self._voting.resolve(session.session_id)

        # Kolektif hafizaya kaydet
        self._memory.store(
            f"decision:{topic}",
            {"winner": winner, "votes": votes},
            confidence=0.9,
        )

        return {
            "success": True,
            "session_id": session.session_id,
            "winner": winner,
            "total_votes": len(votes),
        }

    def handle_failure(
        self,
        agent_id: str,
        task_id: str = "",
        fault_type: str = "unknown",
    ) -> dict[str, Any]:
        """Hata isle.

        Args:
            agent_id: Basarisiz agent.
            task_id: Gorev ID.
            fault_type: Hata tipi.

        Returns:
            Isleme sonucu.
        """
        event = self._fault.report_failure(agent_id, task_id, fault_type)

        # Alarm feromon birak
        swarm = self._coordinator.get_agent_swarm(agent_id)
        if swarm:
            self._pheromones.leave_marker(
                agent_id, f"agent:{agent_id}",
                PheromoneType.ALARM, 1.0,
                {"fault_type": fault_type},
            )

        # Gorev yeniden ata
        reassigned_to = ""
        if task_id:
            healthy = self._fault.get_healthy_agents()
            reassigned_to = self._fault.reassign_task(
                task_id, agent_id, healthy,
            )

        return {
            "success": True,
            "event_id": event.event_id,
            "action": event.action_taken.value,
            "reassigned_to": reassigned_to,
        }

    def share_knowledge(
        self,
        agent_id: str,
        key: str,
        value: Any,
        confidence: float = 0.8,
    ) -> bool:
        """Bilgi paylasimlari.

        Args:
            agent_id: Agent ID.
            key: Anahtar.
            value: Deger.
            confidence: Guven puani.

        Returns:
            Basarili ise True.
        """
        result = self._memory.store(key, value, agent_id, confidence)

        # Basari feromon birak
        if result:
            self._pheromones.leave_marker(
                agent_id, f"knowledge:{key}",
                PheromoneType.SUCCESS, 0.6,
            )

        return result

    def get_collective_knowledge(
        self, pattern: str = "",
    ) -> dict[str, Any]:
        """Kolektif bilgiyi getirir.

        Args:
            pattern: Arama kalibi.

        Returns:
            Bilgi sozlugu.
        """
        if pattern:
            return self._memory.search(pattern)
        return self._memory.get_high_confidence(0.5)

    def optimize(self) -> dict[str, Any]:
        """Suru optimizasyonu yapar.

        Returns:
            Optimizasyon sonucu.
        """
        results: dict[str, Any] = {
            "rebalanced": [],
            "healed": [],
            "decayed_markers": 0,
            "patterns": [],
        }

        # Yuk dengeleme
        transfers = self._balancer.rebalance()
        results["rebalanced"] = transfers

        # Feromon bozunmasi
        decayed = self._pheromones.decay_all()
        results["decayed_markers"] = decayed

        # Oruntu tespiti
        patterns = self._emergent.detect_patterns()
        results["patterns"] = patterns

        # Sagliksiz agent'lari iyilestir
        failed = self._fault.get_failed_agents()
        for agent_id in failed:
            if self._fault.heal_agent(agent_id):
                results["healed"].append(agent_id)

        return results

    def dissolve_mission(self, swarm_id: str) -> bool:
        """Gorevi ve suruyu dagitir.

        Args:
            swarm_id: Suru ID.

        Returns:
            Basarili ise True.
        """
        return self._coordinator.dissolve_swarm(swarm_id)

    def get_snapshot(self) -> SwarmSnapshot:
        """Anlik goruntuyu getirir.

        Returns:
            SwarmSnapshot nesnesi.
        """
        total_swarms = self._coordinator.swarm_count
        active_swarms = self._coordinator.active_swarm_count
        total_members = self._coordinator.total_members

        # Saglik puani
        health = 1.0
        if self._fault.total_events > 0:
            health -= 0.1 * min(self._fault.unresolved_count, 5)
        if total_members > 0:
            health = max(0.0, health * self._fault.healthy_ratio)

        return SwarmSnapshot(
            total_swarms=total_swarms,
            active_swarms=active_swarms,
            total_members=total_members,
            active_auctions=self._auction.open_auction_count,
            active_votes=self._voting.active_sessions,
            total_pheromones=self._pheromones.total_markers,
            fault_events=self._fault.total_events,
            avg_workload=round(self._balancer.avg_load, 3),
            health_score=max(0.0, min(1.0, health)),
        )

    # Alt sistem erisimi
    @property
    def coordinator(self) -> SwarmCoordinator:
        """Suru koordinatoru."""
        return self._coordinator

    @property
    def pheromones(self) -> PheromoneSystem:
        """Feromon sistemi."""
        return self._pheromones

    @property
    def memory(self) -> CollectiveMemory:
        """Kolektif hafiza."""
        return self._memory

    @property
    def voting(self) -> VotingSystem:
        """Oylama sistemi."""
        return self._voting

    @property
    def auction(self) -> TaskAuction:
        """Gorev acik artirma."""
        return self._auction

    @property
    def emergent(self) -> EmergentBehavior:
        """Ortaya cikan davranis."""
        return self._emergent

    @property
    def balancer(self) -> SwarmLoadBalancer:
        """Yuk dengeleyici."""
        return self._balancer

    @property
    def fault(self) -> SwarmFaultTolerance:
        """Hata toleransi."""
        return self._fault
