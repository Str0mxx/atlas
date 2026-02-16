"""ATLAS Sistem Nabız Kontrolcüsü modülü.

Sağlık kontrolleri, bileşen durumu,
bağımlılık sağlığı, yanıt süreleri,
kaynak kullanımı.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class SystemPulseChecker:
    """Sistem nabız kontrolcüsü.

    Tüm bileşenlerin sağlığını izler.

    Attributes:
        _components: Bileşen kayıtları.
        _checks: Kontrol geçmişi.
    """

    def __init__(self) -> None:
        """Kontrolcüyü başlatır."""
        self._components: dict[
            str, dict[str, Any]
        ] = {}
        self._checks: list[
            dict[str, Any]
        ] = []
        self._dependencies: dict[
            str, list[str]
        ] = {}
        self._counter = 0
        self._stats = {
            "checks_performed": 0,
            "components_registered": 0,
        }

        logger.info(
            "SystemPulseChecker baslatildi",
        )

    def register_component(
        self,
        name: str,
        component_type: str = "service",
        endpoint: str = "",
        timeout_ms: float = 5000.0,
    ) -> dict[str, Any]:
        """Bileşen kaydeder.

        Args:
            name: Bileşen adı.
            component_type: Bileşen tipi.
            endpoint: Uç nokta.
            timeout_ms: Zaman aşımı (ms).

        Returns:
            Kayıt bilgisi.
        """
        self._counter += 1
        cid = f"comp_{self._counter}"

        self._components[name] = {
            "component_id": cid,
            "name": name,
            "type": component_type,
            "endpoint": endpoint,
            "timeout_ms": timeout_ms,
            "status": "unknown",
            "last_check": None,
            "response_time_ms": 0.0,
        }
        self._stats[
            "components_registered"
        ] += 1

        return {
            "component_id": cid,
            "name": name,
            "registered": True,
        }

    def check_health(
        self,
        component_name: str,
        response_time_ms: float = 0.0,
        is_healthy: bool = True,
    ) -> dict[str, Any]:
        """Sağlık kontrolü yapar.

        Args:
            component_name: Bileşen adı.
            response_time_ms: Yanıt süresi.
            is_healthy: Sağlıklı mı.

        Returns:
            Kontrol bilgisi.
        """
        comp = self._components.get(
            component_name,
        )
        if not comp:
            return {
                "component": component_name,
                "checked": False,
                "reason": "Not registered",
            }

        status = (
            "healthy"
            if is_healthy
            and response_time_ms
            < comp["timeout_ms"]
            else "degraded"
            if is_healthy
            else "unhealthy"
        )

        comp["status"] = status
        comp["last_check"] = time.time()
        comp["response_time_ms"] = (
            response_time_ms
        )

        check = {
            "component": component_name,
            "status": status,
            "response_time_ms": (
                response_time_ms
            ),
            "timestamp": time.time(),
        }
        self._checks.append(check)
        self._stats[
            "checks_performed"
        ] += 1

        return {
            "component": component_name,
            "status": status,
            "response_time_ms": (
                response_time_ms
            ),
            "checked": True,
        }

    def get_component_status(
        self,
        component_name: str,
    ) -> dict[str, Any]:
        """Bileşen durumu döndürür.

        Args:
            component_name: Bileşen adı.

        Returns:
            Durum bilgisi.
        """
        comp = self._components.get(
            component_name,
        )
        if not comp:
            return {
                "component": component_name,
                "found": False,
            }

        return {
            "component": component_name,
            "status": comp["status"],
            "response_time_ms": comp[
                "response_time_ms"
            ],
            "type": comp["type"],
            "found": True,
        }

    def check_dependency_health(
        self,
        component_name: str,
        dependencies: list[str]
        | None = None,
    ) -> dict[str, Any]:
        """Bağımlılık sağlığı kontrol eder.

        Args:
            component_name: Bileşen adı.
            dependencies: Bağımlılıklar.

        Returns:
            Bağımlılık bilgisi.
        """
        if dependencies:
            self._dependencies[
                component_name
            ] = dependencies

        deps = self._dependencies.get(
            component_name, [],
        )

        healthy_count = 0
        unhealthy = []
        for dep in deps:
            comp = self._components.get(dep)
            if (
                comp
                and comp["status"] == "healthy"
            ):
                healthy_count += 1
            else:
                unhealthy.append(dep)

        total = len(deps) if deps else 1
        health_pct = round(
            healthy_count / total * 100, 1,
        )

        return {
            "component": component_name,
            "dependencies": len(deps),
            "healthy": healthy_count,
            "unhealthy": unhealthy,
            "health_pct": health_pct,
            "all_healthy": len(
                unhealthy,
            ) == 0,
        }

    def measure_response_time(
        self,
        component_name: str,
        response_time_ms: float = 0.0,
    ) -> dict[str, Any]:
        """Yanıt süresi ölçer.

        Args:
            component_name: Bileşen adı.
            response_time_ms: Yanıt süresi.

        Returns:
            Ölçüm bilgisi.
        """
        comp = self._components.get(
            component_name,
        )
        if not comp:
            return {
                "component": component_name,
                "measured": False,
            }

        threshold = comp["timeout_ms"]
        pct_of_timeout = round(
            response_time_ms / threshold * 100,
            1,
        )
        level = (
            "fast"
            if pct_of_timeout < 30
            else "normal"
            if pct_of_timeout < 70
            else "slow"
            if pct_of_timeout < 100
            else "timeout"
        )

        return {
            "component": component_name,
            "response_time_ms": (
                response_time_ms
            ),
            "threshold_ms": threshold,
            "pct_of_timeout": pct_of_timeout,
            "level": level,
            "measured": True,
        }

    def check_resource_usage(
        self,
        component_name: str,
        cpu_pct: float = 0.0,
        memory_pct: float = 0.0,
        disk_pct: float = 0.0,
    ) -> dict[str, Any]:
        """Kaynak kullanımı kontrol eder.

        Args:
            component_name: Bileşen adı.
            cpu_pct: CPU yüzdesi.
            memory_pct: Bellek yüzdesi.
            disk_pct: Disk yüzdesi.

        Returns:
            Kullanım bilgisi.
        """
        avg_usage = round(
            (cpu_pct + memory_pct + disk_pct)
            / 3, 1,
        )

        level = (
            "critical"
            if avg_usage >= 90
            else "high"
            if avg_usage >= 75
            else "normal"
            if avg_usage >= 40
            else "low"
        )

        return {
            "component": component_name,
            "cpu_pct": cpu_pct,
            "memory_pct": memory_pct,
            "disk_pct": disk_pct,
            "avg_usage": avg_usage,
            "level": level,
        }

    @property
    def check_count(self) -> int:
        """Kontrol sayısı."""
        return self._stats[
            "checks_performed"
        ]

    @property
    def component_count(self) -> int:
        """Bileşen sayısı."""
        return self._stats[
            "components_registered"
        ]
