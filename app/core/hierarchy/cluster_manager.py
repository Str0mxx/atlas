"""ATLAS Kume Yoneticisi modulu.

Kume olusturma/silme, agent atama,
saglik izleme, yuk dengeleme ve kumeler arasi iletisim.
"""

import logging
from typing import Any

from app.models.hierarchy import (
    AgentNode,
    ClusterInfo,
    ClusterType,
)

logger = logging.getLogger(__name__)


class ClusterManager:
    """Kume yonetim sistemi.

    Agent kumelerini olusturur, yonetir
    ve saglik durumunu izler.

    Attributes:
        _clusters: Kume haritasi.
        _agent_cluster_map: Agent -> Kume esleme.
    """

    def __init__(self) -> None:
        """Kume yoneticisini baslatir."""
        self._clusters: dict[str, ClusterInfo] = {}
        self._agent_cluster_map: dict[str, str] = {}

        logger.info("ClusterManager baslatildi")

    def create_cluster(
        self,
        name: str,
        cluster_type: ClusterType = ClusterType.CUSTOM,
        max_members: int = 10,
    ) -> ClusterInfo:
        """Kume olusturur.

        Args:
            name: Kume adi.
            cluster_type: Kume tipi.
            max_members: Maks uye sayisi.

        Returns:
            ClusterInfo nesnesi.
        """
        cluster = ClusterInfo(
            name=name,
            cluster_type=cluster_type,
            max_members=max_members,
        )

        self._clusters[cluster.cluster_id] = cluster
        logger.info("Kume olusturuldu: %s (%s)", name, cluster_type.value)
        return cluster

    def destroy_cluster(self, cluster_id: str) -> bool:
        """Kume siler.

        Args:
            cluster_id: Kume ID.

        Returns:
            Basarili ise True.
        """
        if cluster_id not in self._clusters:
            return False

        cluster = self._clusters[cluster_id]

        # Uyeleri cikar
        for member_id in list(cluster.member_ids):
            if member_id in self._agent_cluster_map:
                del self._agent_cluster_map[member_id]

        del self._clusters[cluster_id]
        logger.info("Kume silindi: %s", cluster_id)
        return True

    def assign_agent(
        self,
        agent_id: str,
        cluster_id: str,
        as_leader: bool = False,
    ) -> bool:
        """Agent'i kumeye atar.

        Args:
            agent_id: Agent ID.
            cluster_id: Kume ID.
            as_leader: Lider olarak ata.

        Returns:
            Basarili ise True.
        """
        cluster = self._clusters.get(cluster_id)
        if not cluster:
            return False

        if len(cluster.member_ids) >= cluster.max_members:
            logger.warning(
                "Kume dolu: %s (max=%d)", cluster_id, cluster.max_members,
            )
            return False

        # Onceki kumeden cikar
        if agent_id in self._agent_cluster_map:
            old_cluster_id = self._agent_cluster_map[agent_id]
            old_cluster = self._clusters.get(old_cluster_id)
            if old_cluster and agent_id in old_cluster.member_ids:
                old_cluster.member_ids.remove(agent_id)

        cluster.member_ids.append(agent_id)
        self._agent_cluster_map[agent_id] = cluster_id

        if as_leader:
            cluster.leader_id = agent_id

        return True

    def remove_agent(self, agent_id: str) -> bool:
        """Agent'i kumeden cikarir.

        Args:
            agent_id: Agent ID.

        Returns:
            Basarili ise True.
        """
        if agent_id not in self._agent_cluster_map:
            return False

        cluster_id = self._agent_cluster_map[agent_id]
        cluster = self._clusters.get(cluster_id)

        if cluster and agent_id in cluster.member_ids:
            cluster.member_ids.remove(agent_id)
            if cluster.leader_id == agent_id:
                cluster.leader_id = ""

        del self._agent_cluster_map[agent_id]
        return True

    def get_cluster(self, cluster_id: str) -> ClusterInfo | None:
        """Kume getirir.

        Args:
            cluster_id: Kume ID.

        Returns:
            ClusterInfo veya None.
        """
        return self._clusters.get(cluster_id)

    def get_agent_cluster(self, agent_id: str) -> ClusterInfo | None:
        """Agent'in kumesini getirir.

        Args:
            agent_id: Agent ID.

        Returns:
            ClusterInfo veya None.
        """
        cluster_id = self._agent_cluster_map.get(agent_id)
        if not cluster_id:
            return None
        return self._clusters.get(cluster_id)

    def get_cluster_members(self, cluster_id: str) -> list[str]:
        """Kume uyelerini getirir.

        Args:
            cluster_id: Kume ID.

        Returns:
            Agent ID listesi.
        """
        cluster = self._clusters.get(cluster_id)
        if not cluster:
            return []
        return list(cluster.member_ids)

    def check_cluster_health(
        self,
        cluster_id: str,
        agent_workloads: dict[str, float] | None = None,
    ) -> float:
        """Kume sagligini kontrol eder.

        Args:
            cluster_id: Kume ID.
            agent_workloads: Agent is yukleri.

        Returns:
            Saglik puani (0-1).
        """
        cluster = self._clusters.get(cluster_id)
        if not cluster:
            return 0.0

        score = 1.0

        # Uye sayisi kontrolu
        if not cluster.member_ids:
            score -= 0.5
        elif len(cluster.member_ids) < 2:
            score -= 0.2

        # Lider var mi
        if not cluster.leader_id:
            score -= 0.2

        # Is yuku dengesi
        if agent_workloads:
            loads = [
                agent_workloads.get(mid, 0.0)
                for mid in cluster.member_ids
                if mid in agent_workloads
            ]
            if loads:
                avg = sum(loads) / len(loads)
                if avg > 0.9:
                    score -= 0.3
                elif avg > 0.7:
                    score -= 0.1
                # Dengesizlik
                if len(loads) > 1:
                    variance = sum((l - avg) ** 2 for l in loads) / len(loads)
                    if variance > 0.1:
                        score -= 0.1

        cluster.health_score = max(0.0, min(1.0, score))
        return cluster.health_score

    def balance_load(
        self,
        cluster_id: str,
        agent_workloads: dict[str, float],
    ) -> list[dict[str, str]]:
        """Kume icerisinde yuk dengeleme onerisi verir.

        Args:
            cluster_id: Kume ID.
            agent_workloads: Agent is yukleri.

        Returns:
            Transfer onerileri.
        """
        cluster = self._clusters.get(cluster_id)
        if not cluster or len(cluster.member_ids) < 2:
            return []

        suggestions: list[dict[str, str]] = []

        members_load = [
            (mid, agent_workloads.get(mid, 0.0))
            for mid in cluster.member_ids
        ]

        members_load.sort(key=lambda x: x[1], reverse=True)

        overloaded = [(m, l) for m, l in members_load if l > 0.8]
        underloaded = [(m, l) for m, l in members_load if l < 0.3]

        for over_id, over_load in overloaded:
            for under_id, under_load in underloaded:
                suggestions.append({
                    "from": over_id,
                    "to": under_id,
                    "reason": f"Yuk dengesi: {over_load:.1f} -> {under_load:.1f}",
                })

        return suggestions

    def send_inter_cluster(
        self,
        from_cluster_id: str,
        to_cluster_id: str,
        message: str,
    ) -> dict[str, Any]:
        """Kumeler arasi mesaj gonderir.

        Args:
            from_cluster_id: Kaynak kume.
            to_cluster_id: Hedef kume.
            message: Mesaj.

        Returns:
            Gonderim sonucu.
        """
        from_c = self._clusters.get(from_cluster_id)
        to_c = self._clusters.get(to_cluster_id)

        if not from_c or not to_c:
            return {"success": False, "error": "Kume bulunamadi"}

        return {
            "success": True,
            "from_cluster": from_c.name,
            "to_cluster": to_c.name,
            "message": message,
        }

    def list_clusters(
        self, cluster_type: ClusterType | None = None
    ) -> list[ClusterInfo]:
        """Kumeleri listeler.

        Args:
            cluster_type: Tip filtresi.

        Returns:
            ClusterInfo listesi.
        """
        if cluster_type:
            return [
                c for c in self._clusters.values()
                if c.cluster_type == cluster_type
            ]
        return list(self._clusters.values())

    @property
    def cluster_count(self) -> int:
        """Kume sayisi."""
        return len(self._clusters)
