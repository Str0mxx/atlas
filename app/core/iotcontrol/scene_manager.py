"""ATLAS Sahne Yöneticisi modülü.

Sahne oluşturma, çoklu cihaz kontrolü,
ön ayar yönetimi, aktivasyon tetikleme,
zamanlama.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class SceneManager:
    """Sahne yöneticisi.

    IoT sahnelerini yönetir.

    Attributes:
        _scenes: Sahne kayıtları.
        _presets: Ön ayar kayıtları.
    """

    def __init__(self) -> None:
        """Yöneticiyi başlatır."""
        self._scenes: dict[
            str, dict[str, Any]
        ] = {}
        self._presets: dict[
            str, dict[str, Any]
        ] = {}
        self._counter = 0
        self._stats = {
            "scenes_created": 0,
            "scenes_activated": 0,
        }

        logger.info(
            "SceneManager baslatildi",
        )

    def create_scene(
        self,
        name: str,
        devices: list[dict[str, Any]]
        | None = None,
    ) -> dict[str, Any]:
        """Sahne oluşturur.

        Args:
            name: Sahne adı.
            devices: Cihaz ayarları.

        Returns:
            Oluşturma bilgisi.
        """
        devices = devices or []
        self._counter += 1
        sid = f"scene_{self._counter}"

        self._scenes[sid] = {
            "scene_id": sid,
            "name": name,
            "devices": devices,
            "active": False,
            "created_at": time.time(),
        }

        self._stats[
            "scenes_created"
        ] += 1

        return {
            "scene_id": sid,
            "name": name,
            "device_count": len(devices),
            "created": True,
        }

    def control_devices(
        self,
        scene_id: str,
    ) -> dict[str, Any]:
        """Çoklu cihaz kontrolü yapar.

        Args:
            scene_id: Sahne kimliği.

        Returns:
            Kontrol bilgisi.
        """
        scene = self._scenes.get(scene_id)
        if not scene:
            return {
                "scene_id": scene_id,
                "found": False,
            }

        controlled = []
        for dev in scene["devices"]:
            controlled.append({
                "device_id": dev.get(
                    "device_id", "",
                ),
                "command": dev.get(
                    "command", "",
                ),
                "status": "sent",
            })

        return {
            "scene_id": scene_id,
            "devices_controlled": len(
                controlled,
            ),
            "controlled": True,
        }

    def manage_preset(
        self,
        preset_name: str,
        scene_id: str = "",
        action: str = "save",
    ) -> dict[str, Any]:
        """Ön ayar yönetimi yapar.

        Args:
            preset_name: Ön ayar adı.
            scene_id: Sahne kimliği.
            action: Aksiyon.

        Returns:
            Yönetim bilgisi.
        """
        if action == "save":
            self._presets[preset_name] = {
                "name": preset_name,
                "scene_id": scene_id,
                "saved_at": time.time(),
            }
        elif action == "delete":
            self._presets.pop(
                preset_name, None,
            )

        return {
            "preset_name": preset_name,
            "action": action,
            "managed": True,
        }

    def activate_scene(
        self,
        scene_id: str,
    ) -> dict[str, Any]:
        """Sahneyi aktifler.

        Args:
            scene_id: Sahne kimliği.

        Returns:
            Aktivasyon bilgisi.
        """
        scene = self._scenes.get(scene_id)
        if not scene:
            return {
                "scene_id": scene_id,
                "found": False,
            }

        scene["active"] = True
        self._stats[
            "scenes_activated"
        ] += 1

        return {
            "scene_id": scene_id,
            "name": scene["name"],
            "device_count": len(
                scene["devices"],
            ),
            "activated": True,
        }

    def schedule_scene(
        self,
        scene_id: str,
        cron: str = "",
        time_of_day: str = "",
    ) -> dict[str, Any]:
        """Sahne zamanlar.

        Args:
            scene_id: Sahne kimliği.
            cron: Cron ifadesi.
            time_of_day: Günün saati.

        Returns:
            Zamanlama bilgisi.
        """
        scene = self._scenes.get(scene_id)
        if not scene:
            return {
                "scene_id": scene_id,
                "found": False,
            }

        scene["schedule"] = {
            "cron": cron,
            "time_of_day": time_of_day,
        }

        return {
            "scene_id": scene_id,
            "schedule_type": (
                "cron" if cron
                else "time"
            ),
            "scheduled": True,
        }

    @property
    def scene_count(self) -> int:
        """Sahne sayısı."""
        return self._stats[
            "scenes_created"
        ]

    @property
    def activated_count(self) -> int:
        """Aktivasyon sayısı."""
        return self._stats[
            "scenes_activated"
        ]
