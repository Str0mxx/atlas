"""ATLAS Kopru Orkestratoru modulu.

Tam entegrasyon yonetimi, sistem kesfetme,
otomatik baglama, performans izleme ve sorun giderme.
"""

import logging
from typing import Any

from app.models.bridge import (
    BridgeSnapshot,
    HealthStatus,
    SystemState,
    WorkflowState,
)

from app.core.bridge.api_gateway import APIGateway
from app.core.bridge.config_sync import ConfigSync
from app.core.bridge.data_transformer import DataTransformer
from app.core.bridge.event_router import EventRouter
from app.core.bridge.health_aggregator import HealthAggregator
from app.core.bridge.message_bus import MessageBus
from app.core.bridge.system_registry import SystemRegistry
from app.core.bridge.workflow_connector import WorkflowConnector

logger = logging.getLogger(__name__)


class BridgeOrchestrator:
    """Kopru orkestratoru.

    Tum kopru alt sistemlerini koordine eder,
    sistemleri kesfeder ve otomatik baglar.

    Attributes:
        _registry: Sistem kaydi.
        _bus: Mesaj yolu.
        _events: Olay yonlendirici.
        _gateway: API gecidi.
        _transformer: Veri donusturucu.
        _workflows: Is akisi baglayici.
        _health: Saglik birlestiricisi.
        _config: Konfigurasyon senkronizasyonu.
    """

    def __init__(
        self,
        message_queue_size: int = 1000,
        event_retention: int = 1000,
        auto_discovery: bool = True,
    ) -> None:
        """Orkestratoru baslatir.

        Args:
            message_queue_size: Mesaj kuyrugu boyutu.
            event_retention: Olay tutma limiti.
            auto_discovery: Otomatik kesfetme.
        """
        self._registry = SystemRegistry()
        self._bus = MessageBus(max_queue_size=message_queue_size)
        self._events = EventRouter(retention=event_retention)
        self._gateway = APIGateway()
        self._transformer = DataTransformer()
        self._workflows = WorkflowConnector()
        self._health = HealthAggregator()
        self._config = ConfigSync()
        self._auto_discovery = auto_discovery

        logger.info(
            "BridgeOrchestrator baslatildi "
            "(queue=%d, retention=%d, auto=%s)",
            message_queue_size, event_retention, auto_discovery,
        )

    def register_system(
        self,
        system_id: str,
        name: str,
        capabilities: list[str] | None = None,
        dependencies: list[str] | None = None,
    ) -> dict[str, Any]:
        """Sistemi kaydeder ve baglar.

        Args:
            system_id: Sistem ID.
            name: Sistem adi.
            capabilities: Yetenekler.
            dependencies: Bagimliliklar.

        Returns:
            Kayit sonucu.
        """
        info = self._registry.register(
            system_id, name,
            capabilities=capabilities,
            dependencies=dependencies,
        )

        # Olay yayinla
        self._events.emit(
            "lifecycle", system_id,
            {"action": "registered", "name": name},
        )

        return {
            "success": True,
            "system_id": system_id,
            "name": name,
            "state": info.state.value,
        }

    def activate_system(self, system_id: str) -> dict[str, Any]:
        """Sistemi aktiflestirir.

        Args:
            system_id: Sistem ID.

        Returns:
            Aktivasyon sonucu.
        """
        # Bagimliliklari kontrol et
        deps_met = self._registry.check_dependencies_met(system_id)
        if not deps_met:
            unmet = []
            info = self._registry.get(system_id)
            if info:
                for dep in info.dependencies:
                    dep_info = self._registry.get(dep)
                    if not dep_info or dep_info.state != SystemState.ACTIVE:
                        unmet.append(dep)
            return {
                "success": False,
                "reason": "Karsilanmamis bagimliliklar",
                "unmet": unmet,
            }

        self._registry.activate(system_id)

        # Olay yayinla
        self._events.emit(
            "lifecycle", system_id,
            {"action": "activated"},
        )

        return {
            "success": True,
            "system_id": system_id,
            "state": SystemState.ACTIVE.value,
        }

    def send_message(
        self,
        topic: str,
        payload: dict[str, Any],
        source: str = "",
    ) -> dict[str, Any]:
        """Mesaj gonderir.

        Args:
            topic: Konu.
            payload: Icerik.
            source: Kaynak.

        Returns:
            Gonderim sonucu.
        """
        msg = self._bus.publish(topic, payload, source)

        return {
            "success": True,
            "message_id": msg.message_id,
            "state": msg.state.value,
        }

    def api_request(
        self,
        path: str,
        payload: dict[str, Any] | None = None,
        source: str = "",
    ) -> dict[str, Any]:
        """API istegi yapar.

        Args:
            path: API yolu.
            payload: Veri.
            source: Kaynak.

        Returns:
            API yaniti.
        """
        return self._gateway.request(path, payload, source)

    def execute_workflow(
        self,
        name: str,
        steps: list[str],
        context: dict[str, Any] | None = None,
        systems: list[str] | None = None,
    ) -> dict[str, Any]:
        """Is akisi calistirir.

        Args:
            name: Is akisi adi.
            steps: Adimlar.
            context: Baglam.
            systems: Ilgili sistemler.

        Returns:
            Calisma sonucu.
        """
        workflow = self._workflows.create_workflow(
            name, steps, systems,
        )
        result = self._workflows.execute_workflow(
            workflow.workflow_id, context,
        )

        # Olay yayinla
        self._events.emit(
            "system", "bridge",
            {
                "action": "workflow_completed",
                "workflow_id": workflow.workflow_id,
                "success": result["success"],
            },
        )

        return result

    def check_health(self) -> dict[str, Any]:
        """Tum sistemlerin sagligini kontrol eder.

        Returns:
            Saglik durumu.
        """
        self._health.check_all()
        return self._health.get_aggregate_status()

    def auto_heal(self) -> dict[str, Any]:
        """Sagliksiz sistemleri iyilestirir.

        Returns:
            Iyilestirme sonucu.
        """
        healed = self._health.auto_heal()
        return {
            "healed": healed,
            "count": len(healed),
        }

    def troubleshoot(self, system_id: str) -> dict[str, Any]:
        """Sorun giderir.

        Args:
            system_id: Sistem ID.

        Returns:
            Teshis sonucu.
        """
        issues: list[str] = []
        recommendations: list[str] = []

        # Sistem kayitli mi
        info = self._registry.get(system_id)
        if not info:
            return {
                "system_id": system_id,
                "issues": ["Sistem kayitli degil"],
                "recommendations": ["Sistemi kaydedin"],
            }

        # Durum kontrolu
        if info.state == SystemState.OFFLINE:
            issues.append("Sistem cevrimdisi")
            recommendations.append("Sistemi yeniden baslatin")
        elif info.state == SystemState.DEGRADED:
            issues.append("Sistem dususmus durumda")
            recommendations.append("Saglik kontrolu yapin")

        # Bagimlilik kontrolu
        if not self._registry.check_dependencies_met(system_id):
            issues.append("Karsilanmamis bagimliliklar var")
            recommendations.append("Bagimli sistemleri aktiflestiirin")

        # Saglik kontrolu
        health = self._health.get_health(system_id)
        if health and health.status == HealthStatus.CRITICAL:
            issues.append("Kritik saglik durumu")
            recommendations.append("Kendini iyilestirmeyi deneyin")

        # Devre kesici kontrolu
        if self._gateway.is_circuit_open(system_id):
            issues.append("Devre kesici acik")
            recommendations.append("Devreyi resetleyin")

        if not issues:
            issues.append("Sorun tespit edilmedi")

        return {
            "system_id": system_id,
            "state": info.state.value,
            "issues": issues,
            "recommendations": recommendations,
        }

    def get_snapshot(self) -> BridgeSnapshot:
        """Anlik goruntuyu getirir.

        Returns:
            BridgeSnapshot nesnesi.
        """
        health_status = self._health.get_aggregate_status()
        health_ratio = health_status.get("health_ratio", 1.0)

        return BridgeSnapshot(
            total_systems=self._registry.total_systems,
            active_systems=self._registry.active_count,
            total_messages=self._bus.total_messages,
            pending_messages=self._bus.pending_count,
            total_events=self._events.total_events,
            active_workflows=self._workflows.active_count,
            healthy_systems=self._health.healthy_count,
            avg_health=round(min(1.0, max(0.0, health_ratio)), 3),
        )

    # Alt sistem erisimi
    @property
    def registry(self) -> SystemRegistry:
        """Sistem kaydi."""
        return self._registry

    @property
    def bus(self) -> MessageBus:
        """Mesaj yolu."""
        return self._bus

    @property
    def events(self) -> EventRouter:
        """Olay yonlendirici."""
        return self._events

    @property
    def gateway(self) -> APIGateway:
        """API gecidi."""
        return self._gateway

    @property
    def transformer(self) -> DataTransformer:
        """Veri donusturucu."""
        return self._transformer

    @property
    def workflows(self) -> WorkflowConnector:
        """Is akisi baglayici."""
        return self._workflows

    @property
    def health(self) -> HealthAggregator:
        """Saglik birlestiricisi."""
        return self._health

    @property
    def config(self) -> ConfigSync:
        """Konfigurasyon senkronizasyonu."""
        return self._config
