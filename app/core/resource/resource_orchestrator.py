"""ATLAS Kaynak Orkestratoru modulu.

Tam kaynak yonetimi, capraz kaynak
optimizasyonu, uyari yonetimi,
raporlama ve politika zorlama.
"""

import logging
import time
from typing import Any

from app.models.resource import (
    AlertSeverity,
    CostCategory,
    ResourceAlert,
    ResourceSnapshot,
    ResourceType,
)

from app.core.resource.api_quota_manager import APIQuotaManager
from app.core.resource.capacity_planner import CapacityPlanner
from app.core.resource.cost_tracker import CostTracker
from app.core.resource.cpu_manager import CPUManager
from app.core.resource.memory_manager import MemoryManager
from app.core.resource.network_manager import NetworkManager
from app.core.resource.resource_optimizer import ResourceOptimizer
from app.core.resource.storage_manager import StorageManager

logger = logging.getLogger(__name__)


class ResourceOrchestrator:
    """Kaynak orkestratoru.

    Tum kaynak yoneticilerini koordine
    eder ve birlesik raporlama saglar.

    Attributes:
        cpu: CPU yoneticisi.
        memory: Bellek yoneticisi.
        storage: Depolama yoneticisi.
        network: Ag yoneticisi.
        api_quota: API kota yoneticisi.
        costs: Maliyet takipcisi.
        capacity: Kapasite planlayici.
        optimizer: Kaynak optimizasyonu.
    """

    def __init__(
        self,
        cpu_threshold: float = 0.8,
        memory_threshold: float = 0.8,
        storage_threshold: float = 0.8,
        cost_budget: float = 0.0,
    ) -> None:
        """Orkestratoru baslatir.

        Args:
            cpu_threshold: CPU uyari esigi.
            memory_threshold: Bellek uyari esigi.
            storage_threshold: Depolama uyari esigi.
            cost_budget: Maliyet butcesi.
        """
        self.cpu = CPUManager(threshold=cpu_threshold)
        self.memory = MemoryManager(threshold=memory_threshold)
        self.storage = StorageManager(threshold=storage_threshold)
        self.network = NetworkManager()
        self.api_quota = APIQuotaManager()
        self.costs = CostTracker(monthly_budget=cost_budget)
        self.capacity = CapacityPlanner()
        self.optimizer = ResourceOptimizer()

        self._alerts: list[ResourceAlert] = []
        self._policies: dict[str, dict[str, Any]] = {}
        self._start_time = time.time()

        logger.info("ResourceOrchestrator baslatildi")

    def record_metrics(
        self,
        cpu_usage: float = 0.0,
        memory_mb: float = 0.0,
        bandwidth_mbps: float = 0.0,
    ) -> dict[str, Any]:
        """Metrikleri kaydeder.

        Args:
            cpu_usage: CPU kullanimi (0.0-1.0).
            memory_mb: Bellek kullanimi (MB).
            bandwidth_mbps: Bant genisligi (Mbps).

        Returns:
            Durum ozeti.
        """
        cpu_status = self.cpu.record_usage(cpu_usage)
        mem_status = self.memory.record_usage(memory_mb)
        net_status = self.network.record_bandwidth(bandwidth_mbps)

        statuses = {
            "cpu": cpu_status.value,
            "memory": mem_status.value,
            "network": net_status.value,
        }

        # Uyari uret
        for res_name, status in statuses.items():
            if status == "critical":
                self._create_alert(
                    ResourceType.CPU if res_name == "cpu"
                    else ResourceType.MEMORY if res_name == "memory"
                    else ResourceType.NETWORK,
                    AlertSeverity.CRITICAL,
                    f"{res_name} kritik seviyede",
                )
            elif status == "warning":
                self._create_alert(
                    ResourceType.CPU if res_name == "cpu"
                    else ResourceType.MEMORY if res_name == "memory"
                    else ResourceType.NETWORK,
                    AlertSeverity.WARNING,
                    f"{res_name} uyari seviyesinde",
                )

        # Optimizasyon kontrolu
        self.optimizer.check_auto_scale(
            "cpu", ResourceType.CPU, cpu_usage,
        )

        return statuses

    def track_api_cost(
        self,
        service: str,
        tokens: int = 0,
        cost: float = 0.0,
    ) -> dict[str, Any]:
        """API maliyetini takip eder.

        Args:
            service: Servis adi.
            tokens: Kullanilan token.
            cost: Maliyet.

        Returns:
            Takip sonucu.
        """
        quota_result = self.api_quota.record_call(
            service, tokens,
        )

        if cost > 0:
            self.costs.record_cost(
                CostCategory.API_CALL, cost, service,
            )

        return quota_result

    def add_policy(
        self,
        name: str,
        resource_type: ResourceType,
        rules: dict[str, Any],
    ) -> dict[str, Any]:
        """Politika ekler.

        Args:
            name: Politika adi.
            resource_type: Kaynak turu.
            rules: Kurallar.

        Returns:
            Politika bilgisi.
        """
        policy = {
            "name": name,
            "resource_type": resource_type.value,
            "rules": rules,
            "enabled": True,
        }
        self._policies[name] = policy
        return policy

    def get_health_report(self) -> dict[str, Any]:
        """Saglik raporu olusturur.

        Returns:
            Rapor.
        """
        return {
            "cpu": {
                "usage": self.cpu.current_usage,
                "processes": self.cpu.process_count,
                "cores_allocated": self.cpu.allocated_cores,
            },
            "memory": {
                "used_mb": self.memory.used_mb,
                "available_mb": self.memory.available_mb,
                "allocations": self.memory.allocation_count,
            },
            "storage": {
                "volumes": self.storage.volume_count,
                "files": self.storage.file_count,
            },
            "network": {
                "bandwidth_mbps": self.network.current_bandwidth,
                "connections": self.network.connection_count,
            },
            "api": {
                "quotas": self.api_quota.quota_count,
                "total_cost": self.api_quota.get_total_cost(),
            },
            "costs": {
                "total": self.costs.get_total_cost(),
                "alerts": self.costs.alert_count,
            },
            "alerts": {
                "total": len(self._alerts),
                "unresolved": sum(
                    1 for a in self._alerts if not a.resolved
                ),
            },
        }

    def get_snapshot(self) -> ResourceSnapshot:
        """Kaynak goruntusunu getirir.

        Returns:
            Goruntusu.
        """
        return ResourceSnapshot(
            cpu_usage=self.cpu.current_usage,
            memory_usage=self.memory.get_usage_ratio(),
            storage_usage=0.0,
            network_usage=(
                self.network.current_bandwidth / 1000.0
            ),
            api_quota_used=0.0,
            total_cost=self.costs.get_total_cost(),
            active_alerts=sum(
                1 for a in self._alerts if not a.resolved
            ),
            optimizations_applied=self.optimizer.action_count,
        )

    def resolve_alert(
        self,
        alert_id: str,
    ) -> bool:
        """Uyariyi cozumler.

        Args:
            alert_id: Uyari ID.

        Returns:
            Basarili ise True.
        """
        for alert in self._alerts:
            if alert.alert_id == alert_id:
                alert.resolved = True
                return True
        return False

    def _create_alert(
        self,
        resource_type: ResourceType,
        severity: AlertSeverity,
        message: str,
    ) -> ResourceAlert:
        """Uyari olusturur.

        Args:
            resource_type: Kaynak turu.
            severity: Onem derecesi.
            message: Mesaj.

        Returns:
            Uyari.
        """
        alert = ResourceAlert(
            resource_type=resource_type,
            severity=severity,
            message=message,
        )
        self._alerts.append(alert)
        logger.warning(
            "Kaynak uyarisi: [%s] %s - %s",
            severity.value, resource_type.value, message,
        )
        return alert

    @property
    def alert_count(self) -> int:
        """Uyari sayisi."""
        return len(self._alerts)

    @property
    def policy_count(self) -> int:
        """Politika sayisi."""
        return len(self._policies)
