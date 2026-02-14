"""ATLAS Hiyerarsi Orkestratoru modulu.

Tam hiyerarsi yonetimi, dinamik yapilandirma,
saglik izleme, performans optimizasyonu ve gorsellestirme destegi.
"""

import logging
from typing import Any

from app.models.hierarchy import (
    AgentNode,
    AuthorityLevel,
    AutonomyLevel,
    ClusterType,
    CommandType,
    ConflictType,
    HierarchySnapshot,
)

from app.core.hierarchy.agent_hierarchy import AgentHierarchy
from app.core.hierarchy.autonomy_controller import AutonomyController
from app.core.hierarchy.cluster_manager import ClusterManager
from app.core.hierarchy.command_chain import CommandChain
from app.core.hierarchy.conflict_arbiter import ConflictArbiter
from app.core.hierarchy.delegation_engine import DelegationEngine
from app.core.hierarchy.reporting_system import ReportingSystem
from app.core.hierarchy.supervision_controller import SupervisionController

logger = logging.getLogger(__name__)


class HierarchyOrchestrator:
    """Hiyerarsi orkestratoru.

    Tum alt sistemleri koordine eder, dinamik
    yapilandirma ve optimizasyon saglar.

    Attributes:
        _hierarchy: Agent hiyerarsisi.
        _clusters: Kume yoneticisi.
        _delegation: Yetki devri motoru.
        _supervision: Denetim kontrolcusu.
        _reporting: Raporlama sistemi.
        _commands: Komut zinciri.
        _autonomy: Otonomi kontrolcusu.
        _conflicts: Catisma hakemi.
    """

    def __init__(
        self,
        max_depth: int = 5,
        default_autonomy: str = "medium",
        escalation_timeout: int = 300,
    ) -> None:
        """Orkestratoru baslatir.

        Args:
            max_depth: Maks hiyerarsi derinligi.
            default_autonomy: Varsayilan otonomi seviyesi.
            escalation_timeout: Eskalasyon zaman asimi.
        """
        autonomy_level = AutonomyLevel(default_autonomy)

        self._hierarchy = AgentHierarchy(max_depth=max_depth)
        self._clusters = ClusterManager()
        self._delegation = DelegationEngine()
        self._supervision = SupervisionController(
            escalation_timeout=escalation_timeout,
        )
        self._reporting = ReportingSystem()
        self._commands = CommandChain()
        self._autonomy = AutonomyController(default_level=autonomy_level)
        self._conflicts = ConflictArbiter()

        logger.info(
            "HierarchyOrchestrator baslatildi "
            "(depth=%d, autonomy=%s, timeout=%d)",
            max_depth, default_autonomy, escalation_timeout,
        )

    def setup_agent(
        self,
        name: str,
        authority: AuthorityLevel = AuthorityLevel.WORKER,
        autonomy: AutonomyLevel = AutonomyLevel.MEDIUM,
        parent_id: str = "",
        cluster_id: str = "",
        capabilities: list[str] | None = None,
    ) -> AgentNode:
        """Agent kurar (hiyerarsi + kume + otonomi).

        Args:
            name: Agent adi.
            authority: Yetki seviyesi.
            autonomy: Otonomi seviyesi.
            parent_id: Ust agent ID.
            cluster_id: Kume ID.
            capabilities: Yetenekler.

        Returns:
            AgentNode nesnesi.
        """
        # Hiyerarsiye ekle
        agent = self._hierarchy.add_agent(
            name=name,
            authority=authority,
            autonomy=autonomy,
            parent_id=parent_id,
            capabilities=capabilities,
        )

        # Kumeye ata
        if cluster_id:
            self._clusters.assign_agent(agent.agent_id, cluster_id)
            agent.cluster_id = cluster_id

        # Otonomi ayarla
        self._autonomy.set_autonomy(agent.agent_id, autonomy)

        logger.info(
            "Agent kuruldu: %s (auth=%s, auto=%s, cluster=%s)",
            name, authority.value, autonomy.value, cluster_id,
        )
        return agent

    def delegate_task(
        self,
        from_agent_id: str,
        task_id: str,
        required_capabilities: list[str] | None = None,
        priority: int = 5,
        deadline_minutes: int = 0,
    ) -> dict[str, Any]:
        """Gorevi uygun agent'a devreder.

        Args:
            from_agent_id: Delege eden agent.
            task_id: Gorev ID.
            required_capabilities: Gereken yetenekler.
            priority: Oncelik.
            deadline_minutes: Son tarih.

        Returns:
            Delegasyon sonucu.
        """
        # Alt agent'lari bul
        children = self._hierarchy.get_children(from_agent_id)
        if not children:
            return {"success": False, "reason": "Alt agent yok"}

        # Yetenek eslestirmesi
        if required_capabilities:
            matched = self._delegation.match_capability(
                required_capabilities, children,
            )
            if not matched:
                return {"success": False, "reason": "Uygun agent bulunamadi"}
            target = matched[0]
        else:
            # En az yuklu agent
            target = min(children, key=lambda a: a.workload)

        # Delegasyon yetki kontrolu
        if not self._hierarchy.can_delegate(from_agent_id, target.agent_id):
            return {"success": False, "reason": "Delegasyon yetkisi yok"}

        # Delege et
        record = self._delegation.delegate(
            task_id=task_id,
            from_agent=from_agent_id,
            to_agent=target.agent_id,
            priority=priority,
            deadline_minutes=deadline_minutes,
        )

        # Komut gonder
        self._commands.send_directive(
            from_agent=from_agent_id,
            to_agents=[target.agent_id],
            content=f"Gorev devredildi: {task_id}",
            priority=priority,
        )

        return {
            "success": True,
            "delegation_id": record.delegation_id,
            "to_agent": target.agent_id,
            "to_name": target.name,
        }

    def check_action(
        self, agent_id: str, action: str,
    ) -> dict[str, Any]:
        """Aksiyon izni kontrol eder.

        Args:
            agent_id: Agent ID.
            action: Aksiyon adi.

        Returns:
            Izin bilgisi.
        """
        can_act = self._autonomy.can_act_independently(agent_id, action)
        should_report = self._autonomy.should_report(agent_id, action)

        return {
            "agent_id": agent_id,
            "action": action,
            "can_act": can_act,
            "needs_permission": not can_act,
            "should_report": should_report,
        }

    def report_conflict(
        self,
        conflict_type: ConflictType,
        agents: list[str],
        resource: str = "",
        description: str = "",
        agent_priorities: dict[str, int] | None = None,
    ) -> dict[str, Any]:
        """Catisma bildirir ve cozer.

        Args:
            conflict_type: Catisma tipi.
            agents: Ilgili agent'lar.
            resource: Kaynak.
            description: Aciklama.
            agent_priorities: Agent oncelikleri.

        Returns:
            Cozum sonucu.
        """
        record = self._conflicts.report_conflict(
            conflict_type=conflict_type,
            agents=agents,
            resource=resource,
            description=description,
        )

        # Otomatik cozum dene
        winner = ""
        if agent_priorities:
            winner = self._conflicts.resolve_by_priority(
                record.conflict_id, agent_priorities,
            )

        return {
            "conflict_id": record.conflict_id,
            "resolved": record.resolved,
            "winner": winner,
            "type": conflict_type.value,
        }

    def send_command(
        self,
        from_agent: str,
        content: str,
        to_agents: list[str] | None = None,
        command_type: str = "directive",
        priority: int = 5,
    ) -> dict[str, Any]:
        """Komut gonderir.

        Args:
            from_agent: Gonderen agent.
            content: Icerik.
            to_agents: Hedef agent'lar.
            command_type: Komut tipi.
            priority: Oncelik.

        Returns:
            Gonderim sonucu.
        """
        targets = to_agents or []

        if command_type == "broadcast":
            cmd = self._commands.send_broadcast(
                from_agent, content, targets, priority,
            )
        elif command_type == "emergency":
            cmd = self._commands.send_emergency(
                from_agent, content, targets,
            )
        elif command_type == "feedback":
            cmd = self._commands.send_feedback(
                from_agent, targets[0] if targets else "", content,
            )
        else:
            cmd = self._commands.send_directive(
                from_agent, targets, content, priority,
            )

        return {
            "command_id": cmd.command_id,
            "type": cmd.command_type.value,
            "targets": len(cmd.to_agents),
        }

    def get_snapshot(self) -> HierarchySnapshot:
        """Anlık goruntuyu getirir.

        Returns:
            HierarchySnapshot nesnesi.
        """
        agents = self._hierarchy.all_agents
        active = [a for a in agents if a.active]

        avg_workload = 0.0
        if active:
            avg_workload = sum(a.workload for a in active) / len(active)

        # Saglik puani
        health = 1.0
        if self._conflicts.active_conflicts > 0:
            health -= 0.1 * min(self._conflicts.active_conflicts, 5)
        if self._supervision.intervention_count > 0:
            health -= 0.05 * min(self._supervision.intervention_count, 5)

        return HierarchySnapshot(
            total_agents=len(agents),
            active_agents=len(active),
            total_clusters=self._clusters.cluster_count,
            pending_delegations=self._delegation.active_delegations,
            active_conflicts=self._conflicts.active_conflicts,
            avg_workload=round(avg_workload, 3),
            health_score=max(0.0, min(1.0, health)),
        )

    def get_tree_view(self, agent_id: str | None = None) -> dict[str, Any]:
        """Agac goruntusunu getirir (gorsellestirme destegi).

        Args:
            agent_id: Baslangic agent ID (None ise root).

        Returns:
            Agac yapisi.
        """
        root_id = agent_id or self._hierarchy._root_id
        root = self._hierarchy.get_agent(root_id)

        if not root:
            return {}

        return self._build_tree(root)

    def restructure(
        self,
        agent_id: str,
        new_parent_id: str,
    ) -> bool:
        """Hiyerarsiyi yeniden yapilandirir.

        Args:
            agent_id: Tasinacak agent.
            new_parent_id: Yeni parent.

        Returns:
            Basarili ise True.
        """
        agent = self._hierarchy.get_agent(agent_id)
        new_parent = self._hierarchy.get_agent(new_parent_id)

        if not agent or not new_parent:
            return False

        # Eski parent'tan cikar
        old_parent = self._hierarchy.get_parent(agent_id)
        if old_parent and agent_id in old_parent.children_ids:
            old_parent.children_ids.remove(agent_id)

        # Yeni parent'a ekle
        new_parent.children_ids.append(agent_id)
        agent.parent_id = new_parent_id

        logger.info(
            "Yeniden yapilandirma: %s -> parent=%s",
            agent.name, new_parent.name,
        )
        return True

    def optimize_workload(self) -> list[dict[str, Any]]:
        """Is yuku optimizasyonu yapar.

        Returns:
            Optimizasyon onerileri.
        """
        suggestions: list[dict[str, Any]] = []
        agents = self._hierarchy.all_agents

        overloaded = [a for a in agents if a.workload > 0.8 and a.active]
        underloaded = [a for a in agents if a.workload < 0.3 and a.active]

        for over in overloaded:
            for under in underloaded:
                # Ayni cluster'da mi
                if over.cluster_id == under.cluster_id:
                    suggestions.append({
                        "type": "transfer",
                        "from": over.agent_id,
                        "from_name": over.name,
                        "to": under.agent_id,
                        "to_name": under.name,
                        "reason": f"Yuk dengesi: {over.workload:.1f} -> {under.workload:.1f}",
                    })

        return suggestions

    def _build_tree(self, node: AgentNode) -> dict[str, Any]:
        """Agac yapisi olusturur (recursive)."""
        children = self._hierarchy.get_children(node.agent_id)

        return {
            "id": node.agent_id,
            "name": node.name,
            "authority": node.authority.value,
            "autonomy": node.autonomy.value,
            "workload": node.workload,
            "active": node.active,
            "children": [self._build_tree(c) for c in children],
        }

    # Alt sistem erisimi
    @property
    def hierarchy(self) -> AgentHierarchy:
        """Agent hiyerarsisi."""
        return self._hierarchy

    @property
    def clusters(self) -> ClusterManager:
        """Kume yoneticisi."""
        return self._clusters

    @property
    def delegation(self) -> DelegationEngine:
        """Yetki devri motoru."""
        return self._delegation

    @property
    def supervision(self) -> SupervisionController:
        """Denetim kontrolcusu."""
        return self._supervision

    @property
    def reporting(self) -> ReportingSystem:
        """Raporlama sistemi."""
        return self._reporting

    @property
    def commands(self) -> CommandChain:
        """Komut zinciri."""
        return self._commands

    @property
    def autonomy(self) -> AutonomyController:
        """Otonomi kontrolcusu."""
        return self._autonomy

    @property
    def conflicts(self) -> ConflictArbiter:
        """Catisma hakemi."""
        return self._conflicts
