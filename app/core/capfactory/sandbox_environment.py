"""ATLAS Sandbox Ortamı modülü.

İzole çalıştırma, kaynak limitleri,
güvenlik sınırları, durum izolasyonu,
temizlik.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class SandboxEnvironment:
    """Sandbox ortamı.

    Yetenekleri izole ortamda çalıştırır.

    Attributes:
        _sandboxes: Sandbox kayıtları.
        _resource_limits: Kaynak limitleri.
    """

    def __init__(
        self,
        timeout_seconds: int = 60,
        max_memory_mb: int = 512,
    ) -> None:
        """Sandbox ortamını başlatır.

        Args:
            timeout_seconds: Zaman aşımı (sn).
            max_memory_mb: Maks bellek (MB).
        """
        self._sandboxes: dict[
            str, dict[str, Any]
        ] = {}
        self._resource_limits = {
            "timeout_seconds": timeout_seconds,
            "max_memory_mb": max_memory_mb,
            "max_cpu_percent": 80,
            "max_disk_mb": 1024,
            "max_network_calls": 100,
        }
        self._counter = 0
        self._stats = {
            "sandboxes_created": 0,
            "executions": 0,
            "cleanups": 0,
            "failures": 0,
        }

        logger.info(
            "SandboxEnvironment baslatildi",
        )

    def create_sandbox(
        self,
        name: str = "",
        config: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Sandbox oluşturur.

        Args:
            name: Sandbox adı.
            config: Yapılandırma.

        Returns:
            Sandbox bilgisi.
        """
        self._counter += 1
        sid = f"sandbox_{self._counter}"

        sandbox = {
            "sandbox_id": sid,
            "name": name or f"Sandbox_{sid}",
            "state": "idle",
            "config": config or {},
            "resource_usage": {
                "memory_mb": 0,
                "cpu_percent": 0,
                "disk_mb": 0,
                "network_calls": 0,
            },
            "isolated_state": {},
            "execution_log": [],
            "created_at": time.time(),
        }
        self._sandboxes[sid] = sandbox
        self._stats["sandboxes_created"] += 1

        return {
            "sandbox_id": sid,
            "name": sandbox["name"],
            "state": "idle",
        }

    def execute(
        self,
        sandbox_id: str,
        code: str,
        inputs: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Sandbox'ta kod çalıştırır.

        Args:
            sandbox_id: Sandbox ID.
            code: Çalıştırılacak kod.
            inputs: Girdiler.

        Returns:
            Çalıştırma sonucu.
        """
        sandbox = self._sandboxes.get(sandbox_id)
        if not sandbox:
            return {"error": "sandbox_not_found"}

        sandbox["state"] = "running"
        start_time = time.time()

        # Kaynak limit kontrolü
        if not self._check_resource_limits(
            sandbox,
        ):
            sandbox["state"] = "failed"
            self._stats["failures"] += 1
            return {
                "sandbox_id": sandbox_id,
                "success": False,
                "error": "resource_limit_exceeded",
            }

        # Simüle çalıştırma
        execution = {
            "code_length": len(code),
            "inputs": inputs or {},
            "start_time": start_time,
            "duration_ms": 10.0,
            "success": True,
            "output": {
                "result": "executed_successfully",
            },
        }
        sandbox["execution_log"].append(execution)
        sandbox["state"] = "completed"
        sandbox["resource_usage"]["memory_mb"] += 10
        sandbox["resource_usage"][
            "network_calls"
        ] += 1
        self._stats["executions"] += 1

        return {
            "sandbox_id": sandbox_id,
            "success": True,
            "output": execution["output"],
            "duration_ms": execution["duration_ms"],
        }

    def _check_resource_limits(
        self,
        sandbox: dict[str, Any],
    ) -> bool:
        """Kaynak limitlerini kontrol eder."""
        usage = sandbox["resource_usage"]
        limits = self._resource_limits

        if (
            usage["memory_mb"]
            >= limits["max_memory_mb"]
        ):
            return False
        if (
            usage["network_calls"]
            >= limits["max_network_calls"]
        ):
            return False
        return True

    def get_state(
        self,
        sandbox_id: str,
    ) -> dict[str, Any]:
        """Sandbox durumunu getirir.

        Args:
            sandbox_id: Sandbox ID.

        Returns:
            Durum bilgisi.
        """
        sandbox = self._sandboxes.get(sandbox_id)
        if not sandbox:
            return {"error": "sandbox_not_found"}

        return {
            "sandbox_id": sandbox_id,
            "state": sandbox["state"],
            "resource_usage": dict(
                sandbox["resource_usage"],
            ),
            "executions": len(
                sandbox["execution_log"],
            ),
        }

    def set_resource_limit(
        self,
        resource: str,
        limit: int | float,
    ) -> dict[str, Any]:
        """Kaynak limiti ayarlar.

        Args:
            resource: Kaynak adı.
            limit: Limit değeri.

        Returns:
            Ayar bilgisi.
        """
        key = f"max_{resource}"
        if key not in self._resource_limits:
            key = resource
        self._resource_limits[key] = limit
        return {"resource": resource, "limit": limit}

    def cleanup(
        self,
        sandbox_id: str,
    ) -> dict[str, Any]:
        """Sandbox'ı temizler.

        Args:
            sandbox_id: Sandbox ID.

        Returns:
            Temizleme bilgisi.
        """
        sandbox = self._sandboxes.get(sandbox_id)
        if not sandbox:
            return {"error": "sandbox_not_found"}

        sandbox["state"] = "cleaned"
        sandbox["isolated_state"] = {}
        sandbox["resource_usage"] = {
            "memory_mb": 0,
            "cpu_percent": 0,
            "disk_mb": 0,
            "network_calls": 0,
        }
        self._stats["cleanups"] += 1

        return {
            "sandbox_id": sandbox_id,
            "cleaned": True,
        }

    def cleanup_all(self) -> dict[str, Any]:
        """Tüm sandbox'ları temizler.

        Returns:
            Temizleme bilgisi.
        """
        cleaned = 0
        for sid in list(self._sandboxes.keys()):
            self.cleanup(sid)
            cleaned += 1

        return {"cleaned_count": cleaned}

    def destroy(
        self,
        sandbox_id: str,
    ) -> dict[str, Any]:
        """Sandbox'ı yok eder.

        Args:
            sandbox_id: Sandbox ID.

        Returns:
            Yok etme bilgisi.
        """
        if sandbox_id not in self._sandboxes:
            return {"error": "sandbox_not_found"}

        del self._sandboxes[sandbox_id]
        return {
            "sandbox_id": sandbox_id,
            "destroyed": True,
        }

    @property
    def active_count(self) -> int:
        """Aktif sandbox sayısı."""
        return sum(
            1 for s in self._sandboxes.values()
            if s["state"] in ("idle", "running")
        )

    @property
    def sandbox_count(self) -> int:
        """Toplam sandbox sayısı."""
        return self._stats["sandboxes_created"]

    @property
    def execution_count(self) -> int:
        """Çalıştırma sayısı."""
        return self._stats["executions"]
