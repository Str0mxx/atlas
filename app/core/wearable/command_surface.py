"""Giyilebilir cihaz komut yuzeyi modulu.

Cihazlara komut gonderme, hizli yanit ve
komut durumu takibi saglar.
"""

import logging
import time
import uuid
from typing import Any, Optional

from app.models.wearable_models import CommandSurface

logger = logging.getLogger(__name__)


class WearableCommandSurface:
    """Giyilebilir cihaz komut yuzeyi.

    Komut gonderimi, durum kontrolu ve
    sonuc takibi islevleri saglar.
    """

    def __init__(self) -> None:
        """Komut yuzeyini baslatir."""
        self._commands: dict[str, CommandSurface] = {}
        self._device_commands: dict[str, list[str]] = {}  # device_id -> [surface_ids]
        self._history: list[dict] = []

    def _record_history(self, action: str, **kwargs) -> None:
        """Gecmis kaydina olay ekler."""
        self._history.append({
            "action": action,
            "timestamp": time.time(),
            **kwargs,
        })

    def execute_command(
        self,
        device_id: str,
        command: str,
        payload: Optional[dict[str, Any]] = None,
    ) -> CommandSurface:
        """Cihaza komut gonderir.

        Args:
            device_id: Hedef cihaz kimligi
            command: Komut turu
            payload: Komut verisi

        Returns:
            Olusturulan komut yuzeyi
        """
        surface_id = str(uuid.uuid4())
        surface = CommandSurface(
            surface_id=surface_id,
            device_id=device_id,
            command_type=command,
            payload=payload or {},
            status="pending",
            created_at=time.time(),
        )
        self._commands[surface_id] = surface
        self._device_commands.setdefault(device_id, []).append(surface_id)
        self._record_history(
            "execute_command",
            device_id=device_id,
            surface_id=surface_id,
            command=command,
        )
        logger.info(f"Komut gonderildi: {command} -> {device_id}")
        return surface

    def status_check(self, device_id: str) -> dict[str, Any]:
        """Cihaz hizli durum kontrolu yapar.

        Args:
            device_id: Cihaz kimligi

        Returns:
            Durum bilgisi
        """
        surface = self.execute_command(
            device_id=device_id,
            command="status_check",
            payload={"type": "quick_status"},
        )
        # Simule edilmis durum sonucu
        surface.status = "completed"
        surface.completed_at = time.time()
        surface.result = {
            "device_id": device_id,
            "status": "online",
            "battery": 85,
            "timestamp": time.time(),
        }
        return surface.result

    def quick_reply(self, device_id: str, message: str) -> CommandSurface:
        """Cihazdan hizli yanit gonderir.

        Args:
            device_id: Cihaz kimligi
            message: Yanit mesaji

        Returns:
            Komut yuzeyi
        """
        return self.execute_command(
            device_id=device_id,
            command="quick_reply",
            payload={"message": message},
        )

    def get_pending_commands(self, device_id: str) -> list[CommandSurface]:
        """Bekleyen komutlari listeler.

        Args:
            device_id: Cihaz kimligi

        Returns:
            Bekleyen komut listesi
        """
        surface_ids = self._device_commands.get(device_id, [])
        return [
            self._commands[sid]
            for sid in surface_ids
            if sid in self._commands and self._commands[sid].status == "pending"
        ]

    def complete_command(
        self, surface_id: str, result: Optional[dict[str, Any]] = None
    ) -> bool:
        """Komutu tamamlanmis olarak isaretler.

        Args:
            surface_id: Komut yuzeyi kimligi
            result: Islem sonucu

        Returns:
            Basarili ise True
        """
        surface = self._commands.get(surface_id)
        if not surface:
            return False

        surface.status = "completed"
        surface.completed_at = time.time()
        surface.result = result or {}
        self._record_history(
            "complete_command",
            surface_id=surface_id,
            device_id=surface.device_id,
        )
        logger.info(f"Komut tamamlandi: {surface_id}")
        return True

    def get_history(self) -> list[dict]:
        """Gecmis kayitlarini dondurur."""
        return list(self._history)

    def get_stats(self) -> dict:
        """Istatistikleri dondurur."""
        pending = sum(1 for c in self._commands.values() if c.status == "pending")
        completed = sum(1 for c in self._commands.values() if c.status == "completed")
        return {
            "total_commands": len(self._commands),
            "pending_commands": pending,
            "completed_commands": completed,
            "devices_with_commands": len(self._device_commands),
            "history_count": len(self._history),
        }
