"""ATLAS Yuk Devri Kontrolcusu modulu.

Otomatik yuk devri, manuel yuk devri,
saglik izleme, DNS degisimi
ve trafik yonlendirme.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class FailoverController:
    """Yuk devri kontrolcusu.

    Yuk devri islemlerini yonetir.

    Attributes:
        _nodes: Dugumler.
        _active_node: Aktif dugum.
    """

    def __init__(self) -> None:
        """Kontrolcuyu baslatir."""
        self._nodes: dict[
            str, dict[str, Any]
        ] = {}
        self._active_node: str | None = None
        self._failover_history: list[
            dict[str, Any]
        ] = []
        self._health_checks: dict[
            str, list[dict[str, Any]]
        ] = {}
        self._dns_records: dict[
            str, dict[str, Any]
        ] = {}
        self._traffic_rules: dict[
            str, dict[str, Any]
        ] = {}
        self._stats = {
            "failovers": 0,
            "auto_failovers": 0,
            "manual_failovers": 0,
            "health_checks": 0,
        }

        logger.info(
            "FailoverController baslatildi",
        )

    def add_node(
        self,
        node_id: str,
        endpoint: str = "",
        region: str = "",
        priority: int = 5,
        is_primary: bool = False,
    ) -> dict[str, Any]:
        """Dugum ekler.

        Args:
            node_id: Dugum ID.
            endpoint: Endpoint.
            region: Bolge.
            priority: Oncelik.
            is_primary: Birincil mi.

        Returns:
            Dugum bilgisi.
        """
        self._nodes[node_id] = {
            "endpoint": endpoint,
            "region": region,
            "priority": priority,
            "is_primary": is_primary,
            "status": "healthy",
            "added_at": time.time(),
        }

        self._health_checks[node_id] = []

        if is_primary:
            self._active_node = node_id

        return {
            "node_id": node_id,
            "status": "added",
        }

    def remove_node(
        self,
        node_id: str,
    ) -> bool:
        """Dugum kaldirir.

        Args:
            node_id: Dugum ID.

        Returns:
            Basarili mi.
        """
        if node_id not in self._nodes:
            return False

        del self._nodes[node_id]
        self._health_checks.pop(node_id, None)

        if self._active_node == node_id:
            self._active_node = None

        return True

    def check_health(
        self,
        node_id: str,
        healthy: bool = True,
        latency_ms: float = 0,
    ) -> dict[str, Any]:
        """Saglik kontrolu yapar.

        Args:
            node_id: Dugum ID.
            healthy: Saglikli mi.
            latency_ms: Gecikme.

        Returns:
            Kontrol sonucu.
        """
        node = self._nodes.get(node_id)
        if not node:
            return {"error": "node_not_found"}

        check = {
            "healthy": healthy,
            "latency_ms": latency_ms,
            "checked_at": time.time(),
        }

        if node_id in self._health_checks:
            self._health_checks[node_id].append(
                check,
            )

        old_status = node["status"]
        node["status"] = (
            "healthy" if healthy else "unhealthy"
        )

        self._stats["health_checks"] += 1

        # Otomatik yuk devri
        trigger_failover = (
            not healthy
            and node_id == self._active_node
        )

        return {
            "node_id": node_id,
            "healthy": healthy,
            "status_changed": (
                old_status != node["status"]
            ),
            "trigger_failover": trigger_failover,
        }

    def failover(
        self,
        target_node: str | None = None,
        mode: str = "automatic",
    ) -> dict[str, Any]:
        """Yuk devri yapar.

        Args:
            target_node: Hedef dugum.
            mode: Mod (automatic/manual).

        Returns:
            Yuk devri sonucu.
        """
        old_node = self._active_node

        if target_node:
            node = self._nodes.get(target_node)
            if not node:
                return {
                    "error": "target_not_found",
                }
            new_node = target_node
        else:
            # En yuksek oncelikli saglikli
            candidates = [
                (nid, n) for nid, n
                in self._nodes.items()
                if n["status"] == "healthy"
                and nid != self._active_node
            ]
            if not candidates:
                return {
                    "error": "no_healthy_nodes",
                }

            candidates.sort(
                key=lambda x: x[1]["priority"],
                reverse=True,
            )
            new_node = candidates[0][0]

        self._active_node = new_node
        self._stats["failovers"] += 1

        if mode == "automatic":
            self._stats["auto_failovers"] += 1
        else:
            self._stats["manual_failovers"] += 1

        record = {
            "from_node": old_node,
            "to_node": new_node,
            "mode": mode,
            "timestamp": time.time(),
        }
        self._failover_history.append(record)

        return {
            "from_node": old_node,
            "to_node": new_node,
            "mode": mode,
            "status": "completed",
        }

    def set_dns_record(
        self,
        domain: str,
        target: str,
        ttl: int = 60,
    ) -> dict[str, Any]:
        """DNS kaydi ayarlar.

        Args:
            domain: Domain.
            target: Hedef.
            ttl: TTL.

        Returns:
            DNS bilgisi.
        """
        self._dns_records[domain] = {
            "target": target,
            "ttl": ttl,
            "updated_at": time.time(),
        }

        return {
            "domain": domain,
            "target": target,
        }

    def switch_dns(
        self,
        domain: str,
        new_target: str,
    ) -> dict[str, Any]:
        """DNS degistirir.

        Args:
            domain: Domain.
            new_target: Yeni hedef.

        Returns:
            Degisim bilgisi.
        """
        old = self._dns_records.get(domain)
        old_target = (
            old["target"] if old else None
        )

        self._dns_records[domain] = {
            "target": new_target,
            "ttl": old["ttl"] if old else 60,
            "updated_at": time.time(),
        }

        return {
            "domain": domain,
            "old_target": old_target,
            "new_target": new_target,
        }

    def add_traffic_rule(
        self,
        rule_id: str,
        source: str = "",
        target: str = "",
        weight: int = 100,
    ) -> dict[str, Any]:
        """Trafik kurali ekler.

        Args:
            rule_id: Kural ID.
            source: Kaynak.
            target: Hedef.
            weight: Agirlik.

        Returns:
            Kural bilgisi.
        """
        self._traffic_rules[rule_id] = {
            "source": source,
            "target": target,
            "weight": weight,
        }

        return {
            "rule_id": rule_id,
            "weight": weight,
        }

    def get_active_node(self) -> str | None:
        """Aktif dugumu getirir.

        Returns:
            Aktif dugum ID veya None.
        """
        return self._active_node

    def get_node(
        self,
        node_id: str,
    ) -> dict[str, Any] | None:
        """Dugum bilgisi getirir.

        Args:
            node_id: Dugum ID.

        Returns:
            Dugum bilgisi veya None.
        """
        return self._nodes.get(node_id)

    def list_nodes(
        self,
        healthy_only: bool = False,
    ) -> list[dict[str, Any]]:
        """Dugumleri listeler.

        Args:
            healthy_only: Sadece saglikliler.

        Returns:
            Dugum listesi.
        """
        nodes = [
            {"node_id": nid, **n}
            for nid, n in self._nodes.items()
        ]
        if healthy_only:
            nodes = [
                n for n in nodes
                if n["status"] == "healthy"
            ]
        return nodes

    def get_history(
        self,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """Yuk devri gecmisini getirir.

        Args:
            limit: Limit.

        Returns:
            Gecmis listesi.
        """
        return self._failover_history[-limit:]

    @property
    def node_count(self) -> int:
        """Dugum sayisi."""
        return len(self._nodes)

    @property
    def failover_count(self) -> int:
        """Yuk devri sayisi."""
        return self._stats["failovers"]

    @property
    def auto_failover_count(self) -> int:
        """Otomatik yuk devri sayisi."""
        return self._stats["auto_failovers"]

    @property
    def dns_record_count(self) -> int:
        """DNS kayit sayisi."""
        return len(self._dns_records)

    @property
    def traffic_rule_count(self) -> int:
        """Trafik kurali sayisi."""
        return len(self._traffic_rules)
