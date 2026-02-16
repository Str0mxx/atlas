"""ATLAS Cihaz Komutacısı modülü.

Komut gönderme, durum yönetimi,
toplu komutlar, yanıt işleme,
yeniden deneme mantığı.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class DeviceCommander:
    """Cihaz komutacısı.

    Cihazlara komut gönderir ve yönetir.

    Attributes:
        _devices: Cihaz durumları.
        _commands: Komut kayıtları.
    """

    def __init__(self) -> None:
        """Komutacıyı başlatır."""
        self._devices: dict[
            str, dict[str, Any]
        ] = {}
        self._commands: list[
            dict[str, Any]
        ] = []
        self._counter = 0
        self._stats = {
            "commands_sent": 0,
            "commands_failed": 0,
        }

        logger.info(
            "DeviceCommander baslatildi",
        )

    def send_command(
        self,
        device_id: str,
        command: str,
        params: dict[str, Any]
        | None = None,
    ) -> dict[str, Any]:
        """Komut gönderir.

        Args:
            device_id: Cihaz kimliği.
            command: Komut.
            params: Parametreler.

        Returns:
            Gönderim bilgisi.
        """
        params = params or {}
        self._counter += 1
        cid = f"cmd_{self._counter}"

        cmd = {
            "command_id": cid,
            "device_id": device_id,
            "command": command,
            "params": params,
            "status": "sent",
            "timestamp": time.time(),
        }
        self._commands.append(cmd)
        self._stats["commands_sent"] += 1

        return {
            "command_id": cid,
            "device_id": device_id,
            "command": command,
            "status": "sent",
            "sent": True,
        }

    def manage_state(
        self,
        device_id: str,
        state: dict[str, Any]
        | None = None,
    ) -> dict[str, Any]:
        """Durum yönetimi yapar.

        Args:
            device_id: Cihaz kimliği.
            state: Durum.

        Returns:
            Durum bilgisi.
        """
        state = state or {}

        if device_id not in self._devices:
            self._devices[device_id] = {}

        self._devices[device_id].update(
            state,
        )

        return {
            "device_id": device_id,
            "state": self._devices[
                device_id
            ],
            "managed": True,
        }

    def batch_command(
        self,
        device_ids: list[str]
        | None = None,
        command: str = "",
        params: dict[str, Any]
        | None = None,
    ) -> dict[str, Any]:
        """Toplu komut gönderir.

        Args:
            device_ids: Cihaz kimlikleri.
            command: Komut.
            params: Parametreler.

        Returns:
            Toplu bilgi.
        """
        device_ids = device_ids or []
        params = params or {}

        results = []
        for did in device_ids:
            r = self.send_command(
                did, command, params,
            )
            results.append(r)

        return {
            "command": command,
            "device_count": len(
                device_ids,
            ),
            "sent_count": len(results),
            "batch_sent": True,
        }

    def handle_response(
        self,
        command_id: str,
        success: bool = True,
        response_data: dict[str, Any]
        | None = None,
    ) -> dict[str, Any]:
        """Yanıt işler.

        Args:
            command_id: Komut kimliği.
            success: Başarılı mı.
            response_data: Yanıt verisi.

        Returns:
            İşleme bilgisi.
        """
        response_data = (
            response_data or {}
        )

        for cmd in self._commands:
            if cmd["command_id"] == command_id:
                cmd["status"] = (
                    "acknowledged"
                    if success
                    else "failed"
                )
                cmd["response"] = (
                    response_data
                )
                if not success:
                    self._stats[
                        "commands_failed"
                    ] += 1
                return {
                    "command_id": command_id,
                    "success": success,
                    "handled": True,
                }

        return {
            "command_id": command_id,
            "found": False,
        }

    def retry_command(
        self,
        command_id: str,
        max_retries: int = 3,
    ) -> dict[str, Any]:
        """Komut yeniden dener.

        Args:
            command_id: Komut kimliği.
            max_retries: Maksimum deneme.

        Returns:
            Yeniden deneme bilgisi.
        """
        original = None
        for cmd in self._commands:
            if cmd["command_id"] == command_id:
                original = cmd
                break

        if not original:
            return {
                "command_id": command_id,
                "found": False,
            }

        retry = self.send_command(
            original["device_id"],
            original["command"],
            original.get("params", {}),
        )

        return {
            "original_id": command_id,
            "retry_id": retry[
                "command_id"
            ],
            "max_retries": max_retries,
            "retried": True,
        }

    @property
    def command_count(self) -> int:
        """Komut sayısı."""
        return self._stats[
            "commands_sent"
        ]

    @property
    def failed_count(self) -> int:
        """Başarısız sayısı."""
        return self._stats[
            "commands_failed"
        ]
