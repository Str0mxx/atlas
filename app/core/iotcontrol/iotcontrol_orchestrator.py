"""ATLAS IoT Kontrol Orkestratörü.

Tam IoT yönetim pipeline,
Discover → Connect → Control → Monitor,
akıllı otomasyon, analitik.
"""

import logging
from typing import Any

from app.core.iotcontrol.automation_rule_engine import (
    AutomationRuleEngine,
)
from app.core.iotcontrol.device_commander import (
    DeviceCommander,
)
from app.core.iotcontrol.device_discovery import (
    DeviceDiscovery,
)
from app.core.iotcontrol.device_health_monitor import (
    DeviceHealthMonitor,
)
from app.core.iotcontrol.mqtt_bridge import (
    MQTTBridge,
)
from app.core.iotcontrol.protocol_adapter import (
    ProtocolAdapter,
)
from app.core.iotcontrol.scene_manager import (
    SceneManager,
)
from app.core.iotcontrol.sensor_data_collector import (
    SensorDataCollector,
)

logger = logging.getLogger(__name__)


class IoTControlOrchestrator:
    """IoT kontrol orkestratörü.

    Tüm IoT bileşenlerini koordine eder.

    Attributes:
        discovery: Cihaz keşifçisi.
        mqtt: MQTT köprüsü.
        commander: Cihaz komutacısı.
        sensors: Sensör toplayıcı.
        rules: Otomasyon motoru.
        health: Sağlık izleyici.
        scenes: Sahne yöneticisi.
        protocols: Protokol adaptörü.
    """

    def __init__(self) -> None:
        """Orkestratörü başlatır."""
        self.discovery = DeviceDiscovery()
        self.mqtt = MQTTBridge()
        self.commander = DeviceCommander()
        self.sensors = (
            SensorDataCollector()
        )
        self.rules = (
            AutomationRuleEngine()
        )
        self.health = (
            DeviceHealthMonitor()
        )
        self.scenes = SceneManager()
        self.protocols = ProtocolAdapter()
        self._stats = {
            "pipelines_run": 0,
            "devices_managed": 0,
        }

        logger.info(
            "IoTControlOrchestrator "
            "baslatildi",
        )

    def manage_device(
        self,
        device_ip: str,
        protocol: str = "wifi",
        name: str = "",
    ) -> dict[str, Any]:
        """Discover → Connect → Register.

        Args:
            device_ip: Cihaz IP'si.
            protocol: Protokol.
            name: Cihaz adı.

        Returns:
            Pipeline bilgisi.
        """
        # 1. Identify
        identity = (
            self.discovery.identify_device(
                device_ip=device_ip,
            )
        )

        # 2. Register
        reg = (
            self.discovery.auto_register(
                device_id=identity[
                    "device_id"
                ],
                device_ip=device_ip,
                protocol=protocol,
                name=name,
            )
        )

        # 3. Connect MQTT
        self.mqtt.connect()
        self.mqtt.subscribe(
            topic=(
                f"devices/{identity['device_id']}"
            ),
        )

        # 4. Health check
        self.health.check_health(
            identity["device_id"],
        )

        self._stats[
            "pipelines_run"
        ] += 1
        self._stats[
            "devices_managed"
        ] += 1

        return {
            "device_id": identity[
                "device_id"
            ],
            "name": reg["name"],
            "protocol": protocol,
            "registered": True,
            "connected": True,
            "health_checked": True,
            "pipeline_complete": True,
        }

    def smart_control(
        self,
        device_id: str,
        command: str = "",
        params: dict[str, Any]
        | None = None,
    ) -> dict[str, Any]:
        """Akıllı kontrol yapar.

        Args:
            device_id: Cihaz kimliği.
            command: Komut.
            params: Parametreler.

        Returns:
            Kontrol bilgisi.
        """
        params = params or {}

        # Send command
        cmd = self.commander.send_command(
            device_id=device_id,
            command=command,
            params=params,
        )

        # Publish to MQTT
        self.mqtt.publish(
            topic=f"devices/{device_id}/cmd",
            payload=command,
        )

        return {
            "device_id": device_id,
            "command_id": cmd["command_id"],
            "command": command,
            "sent": True,
            "published": True,
        }

    def get_analytics(
        self,
    ) -> dict[str, Any]:
        """Analitik döndürür.

        Returns:
            Analitik bilgisi.
        """
        return {
            "pipelines_run": (
                self._stats[
                    "pipelines_run"
                ]
            ),
            "devices_managed": (
                self._stats[
                    "devices_managed"
                ]
            ),
            "devices_discovered": (
                self.discovery.device_count
            ),
            "commands_sent": (
                self.commander.command_count
            ),
            "messages_published": (
                self.mqtt.published_count
            ),
            "sensor_readings": (
                self.sensors.reading_count
            ),
            "rules_defined": (
                self.rules.rule_count
            ),
            "health_checks": (
                self.health.check_count
            ),
            "scenes_created": (
                self.scenes.scene_count
            ),
            "protocol_translations": (
                self.protocols
                .translation_count
            ),
        }

    @property
    def pipeline_count(self) -> int:
        """Pipeline sayısı."""
        return self._stats[
            "pipelines_run"
        ]

    @property
    def managed_count(self) -> int:
        """Yönetilen cihaz sayısı."""
        return self._stats[
            "devices_managed"
        ]
