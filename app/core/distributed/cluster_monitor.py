"""ATLAS Kume Izleyici modulu.

Dugum sagligi, kaynak izleme,
topoloji takibi, uyari uretimi
ve otomatik olcekleme tetikleyicileri.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class ClusterMonitor:
    """Kume izleyici.

    Kume saglik durumunu izler.

    Attributes:
        _nodes: Dugum bilgileri.
        _alerts: Uyarilar.
    """

    def __init__(
        self,
        alert_threshold: float = 0.8,
    ) -> None:
        """Kume izleyiciyi baslatir.

        Args:
            alert_threshold: Uyari esigi.
        """
        self._nodes: dict[
            str, dict[str, Any]
        ] = {}
        self._alerts: list[
            dict[str, Any]
        ] = []
        self._metrics_history: list[
            dict[str, Any]
        ] = []
        self._alert_threshold = alert_threshold
        self._scaling_rules: list[
            dict[str, Any]
        ] = []

        logger.info(
            "ClusterMonitor baslatildi",
        )

    def register_node(
        self,
        node_id: str,
        host: str = "localhost",
        role: str = "worker",
    ) -> dict[str, Any]:
        """Dugum kaydeder.

        Args:
            node_id: Dugum ID.
            host: Ana bilgisayar.
            role: Rol.

        Returns:
            Dugum bilgisi.
        """
        node = {
            "node_id": node_id,
            "host": host,
            "role": role,
            "status": "active",
            "cpu_usage": 0.0,
            "memory_usage": 0.0,
            "disk_usage": 0.0,
            "last_seen": time.time(),
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

    def update_metrics(
        self,
        node_id: str,
        cpu: float = 0.0,
        memory: float = 0.0,
        disk: float = 0.0,
    ) -> dict[str, Any]:
        """Metrik gunceller.

        Args:
            node_id: Dugum ID.
            cpu: CPU kullanimi.
            memory: Bellek kullanimi.
            disk: Disk kullanimi.

        Returns:
            Guncelleme sonucu.
        """
        node = self._nodes.get(node_id)
        if not node:
            return {
                "status": "error",
                "reason": "node_not_found",
            }

        node["cpu_usage"] = cpu
        node["memory_usage"] = memory
        node["disk_usage"] = disk
        node["last_seen"] = time.time()

        # Uyari kontrol
        alerts = []
        if cpu > self._alert_threshold:
            alerts.append(
                self._create_alert(
                    node_id, "cpu_high",
                    f"CPU: {cpu:.1%}",
                )
            )
        if memory > self._alert_threshold:
            alerts.append(
                self._create_alert(
                    node_id, "memory_high",
                    f"Memory: {memory:.1%}",
                )
            )
        if disk > self._alert_threshold:
            alerts.append(
                self._create_alert(
                    node_id, "disk_high",
                    f"Disk: {disk:.1%}",
                )
            )

        self._metrics_history.append({
            "node_id": node_id,
            "cpu": cpu,
            "memory": memory,
            "disk": disk,
            "timestamp": time.time(),
        })

        return {
            "node_id": node_id,
            "alerts": len(alerts),
            "status": "updated",
        }

    def _create_alert(
        self,
        node_id: str,
        alert_type: str,
        message: str,
    ) -> dict[str, Any]:
        """Uyari olusturur.

        Args:
            node_id: Dugum ID.
            alert_type: Uyari tipi.
            message: Mesaj.

        Returns:
            Uyari bilgisi.
        """
        alert = {
            "node_id": node_id,
            "type": alert_type,
            "message": message,
            "timestamp": time.time(),
        }
        self._alerts.append(alert)
        return alert

    def check_health(self) -> dict[str, Any]:
        """Kume sagligini kontrol eder.

        Returns:
            Saglik bilgisi.
        """
        total = len(self._nodes)
        active = sum(
            1 for n in self._nodes.values()
            if n["status"] == "active"
        )
        failed = sum(
            1 for n in self._nodes.values()
            if n["status"] == "failed"
        )

        avg_cpu = (
            sum(
                n["cpu_usage"]
                for n in self._nodes.values()
            ) / total if total > 0 else 0.0
        )
        avg_memory = (
            sum(
                n["memory_usage"]
                for n in self._nodes.values()
            ) / total if total > 0 else 0.0
        )

        return {
            "total_nodes": total,
            "active": active,
            "failed": failed,
            "avg_cpu": round(avg_cpu, 4),
            "avg_memory": round(avg_memory, 4),
            "healthy": (
                active == total and total > 0
            ),
        }

    def get_topology(self) -> dict[str, Any]:
        """Topoloji getirir.

        Returns:
            Topoloji bilgisi.
        """
        roles: dict[str, list[str]] = {}
        for n in self._nodes.values():
            role = n["role"]
            if role not in roles:
                roles[role] = []
            roles[role].append(n["node_id"])

        return {
            "total_nodes": len(self._nodes),
            "roles": roles,
            "role_count": {
                k: len(v)
                for k, v in roles.items()
            },
        }

    def detect_failures(
        self,
        timeout: float = 60.0,
    ) -> dict[str, Any]:
        """Arizalari tespit eder.

        Args:
            timeout: Zaman asimi (sn).

        Returns:
            Tespit sonucu.
        """
        now = time.time()
        failed = []

        for node in self._nodes.values():
            if node["status"] == "failed":
                continue
            elapsed = now - node["last_seen"]
            if elapsed > timeout:
                node["status"] = "failed"
                failed.append(node["node_id"])
                self._create_alert(
                    node["node_id"],
                    "node_failed",
                    f"Node offline: {elapsed:.0f}s",
                )

        return {
            "checked": len(self._nodes),
            "failed": len(failed),
            "failed_ids": failed,
        }

    def add_scaling_rule(
        self,
        metric: str,
        threshold: float,
        action: str,
    ) -> dict[str, Any]:
        """Olcekleme kurali ekler.

        Args:
            metric: Metrik adi.
            threshold: Esik degeri.
            action: Aksiyon.

        Returns:
            Kural bilgisi.
        """
        rule = {
            "metric": metric,
            "threshold": threshold,
            "action": action,
            "triggered_count": 0,
        }
        self._scaling_rules.append(rule)
        return rule

    def evaluate_scaling(
        self,
    ) -> dict[str, Any]:
        """Olcekleme degerlendirir.

        Returns:
            Degerlendirme sonucu.
        """
        health = self.check_health()
        triggered = []

        for rule in self._scaling_rules:
            metric = rule["metric"]
            if metric == "cpu":
                value = health["avg_cpu"]
            elif metric == "memory":
                value = health["avg_memory"]
            else:
                continue

            if value > rule["threshold"]:
                rule["triggered_count"] += 1
                triggered.append({
                    "metric": metric,
                    "value": value,
                    "threshold": rule["threshold"],
                    "action": rule["action"],
                })

        return {
            "rules_checked": len(
                self._scaling_rules,
            ),
            "triggered": len(triggered),
            "actions": triggered,
        }

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

    @property
    def node_count(self) -> int:
        """Dugum sayisi."""
        return len(self._nodes)

    @property
    def alert_count(self) -> int:
        """Uyari sayisi."""
        return len(self._alerts)

    @property
    def active_count(self) -> int:
        """Aktif dugum sayisi."""
        return sum(
            1 for n in self._nodes.values()
            if n["status"] == "active"
        )
