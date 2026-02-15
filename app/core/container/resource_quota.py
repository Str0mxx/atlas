"""ATLAS Kaynak Kotasi modulu.

CPU/bellek limitleri, depolama kotalari,
isim alani kotalari, limit araliklari
ve oncelik siniflari.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class ResourceQuota:
    """Kaynak kotasi yoneticisi.

    Kume kaynak kotalarini yonetir.

    Attributes:
        _quotas: Namespace kotalari.
        _limit_ranges: Limit araliklari.
    """

    def __init__(self) -> None:
        """Yoneticiyi baslatir."""
        self._quotas: dict[
            str, dict[str, Any]
        ] = {}
        self._limit_ranges: dict[
            str, dict[str, Any]
        ] = {}
        self._priority_classes: dict[
            str, dict[str, Any]
        ] = {}
        self._usage: dict[
            str, dict[str, float]
        ] = {}

        logger.info(
            "ResourceQuota baslatildi",
        )

    def set_quota(
        self,
        namespace: str,
        cpu_limit: str = "4",
        memory_limit: str = "8Gi",
        storage_limit: str = "100Gi",
        pod_limit: int = 50,
    ) -> dict[str, Any]:
        """Namespace kotasi ayarlar.

        Args:
            namespace: Isim alani.
            cpu_limit: CPU limiti.
            memory_limit: Bellek limiti.
            storage_limit: Depolama limiti.
            pod_limit: Pod limiti.

        Returns:
            Kota bilgisi.
        """
        self._quotas[namespace] = {
            "namespace": namespace,
            "cpu_limit": cpu_limit,
            "memory_limit": memory_limit,
            "storage_limit": storage_limit,
            "pod_limit": pod_limit,
            "created_at": time.time(),
        }

        self._usage.setdefault(namespace, {
            "cpu": 0.0,
            "memory": 0.0,
            "storage": 0.0,
            "pods": 0,
        })

        return {
            "namespace": namespace,
            "cpu": cpu_limit,
            "memory": memory_limit,
        }

    def get_quota(
        self,
        namespace: str,
    ) -> dict[str, Any] | None:
        """Kota bilgisini getirir.

        Args:
            namespace: Isim alani.

        Returns:
            Kota bilgisi veya None.
        """
        return self._quotas.get(namespace)

    def delete_quota(
        self,
        namespace: str,
    ) -> bool:
        """Kotayi siler.

        Args:
            namespace: Isim alani.

        Returns:
            Basarili mi.
        """
        if namespace not in self._quotas:
            return False

        del self._quotas[namespace]
        self._usage.pop(namespace, None)
        return True

    def update_usage(
        self,
        namespace: str,
        cpu: float = 0.0,
        memory: float = 0.0,
        storage: float = 0.0,
        pods: int = 0,
    ) -> dict[str, Any]:
        """Kullanim gunceller.

        Args:
            namespace: Isim alani.
            cpu: CPU kullanimi.
            memory: Bellek kullanimi.
            storage: Depolama kullanimi.
            pods: Pod sayisi.

        Returns:
            Kullanim bilgisi.
        """
        self._usage.setdefault(namespace, {
            "cpu": 0.0,
            "memory": 0.0,
            "storage": 0.0,
            "pods": 0,
        })

        usage = self._usage[namespace]
        usage["cpu"] = cpu
        usage["memory"] = memory
        usage["storage"] = storage
        usage["pods"] = pods

        return {
            "namespace": namespace,
            **usage,
        }

    def check_quota(
        self,
        namespace: str,
        request_cpu: float = 0.0,
        request_memory: float = 0.0,
    ) -> dict[str, Any]:
        """Kota kontrolu yapar.

        Args:
            namespace: Isim alani.
            request_cpu: Istenen CPU.
            request_memory: Istenen bellek.

        Returns:
            Kontrol sonucu.
        """
        quota = self._quotas.get(namespace)
        if not quota:
            return {
                "allowed": True,
                "reason": "no_quota",
            }

        usage = self._usage.get(namespace, {})
        current_cpu = usage.get("cpu", 0.0)
        current_memory = usage.get("memory", 0.0)

        cpu_limit = float(quota["cpu_limit"])
        mem_str = quota["memory_limit"]
        mem_limit = self._parse_memory(mem_str)

        cpu_ok = (
            current_cpu + request_cpu <= cpu_limit
        )
        mem_ok = (
            current_memory + request_memory
            <= mem_limit
        )

        return {
            "allowed": cpu_ok and mem_ok,
            "cpu_available": cpu_limit - current_cpu,
            "memory_available": (
                mem_limit - current_memory
            ),
            "cpu_exceeded": not cpu_ok,
            "memory_exceeded": not mem_ok,
        }

    def _parse_memory(self, mem_str: str) -> float:
        """Bellek stringini parse eder.

        Args:
            mem_str: Bellek stringi.

        Returns:
            MB cinsinden deger.
        """
        if mem_str.endswith("Gi"):
            return float(mem_str[:-2]) * 1024
        if mem_str.endswith("Mi"):
            return float(mem_str[:-2])
        if mem_str.endswith("Ki"):
            return float(mem_str[:-2]) / 1024
        return float(mem_str)

    def set_limit_range(
        self,
        namespace: str,
        resource_type: str = "Container",
        min_cpu: str = "100m",
        max_cpu: str = "2",
        min_memory: str = "64Mi",
        max_memory: str = "2Gi",
        default_cpu: str = "500m",
        default_memory: str = "256Mi",
    ) -> dict[str, Any]:
        """Limit araligi ayarlar.

        Args:
            namespace: Isim alani.
            resource_type: Kaynak tipi.
            min_cpu: Min CPU.
            max_cpu: Maks CPU.
            min_memory: Min bellek.
            max_memory: Maks bellek.
            default_cpu: Varsayilan CPU.
            default_memory: Varsayilan bellek.

        Returns:
            Limit araligi bilgisi.
        """
        key = f"{namespace}:{resource_type}"
        self._limit_ranges[key] = {
            "namespace": namespace,
            "type": resource_type,
            "min": {
                "cpu": min_cpu,
                "memory": min_memory,
            },
            "max": {
                "cpu": max_cpu,
                "memory": max_memory,
            },
            "default": {
                "cpu": default_cpu,
                "memory": default_memory,
            },
            "created_at": time.time(),
        }

        return {
            "namespace": namespace,
            "type": resource_type,
        }

    def get_limit_range(
        self,
        namespace: str,
        resource_type: str = "Container",
    ) -> dict[str, Any] | None:
        """Limit araligini getirir.

        Args:
            namespace: Isim alani.
            resource_type: Kaynak tipi.

        Returns:
            Limit bilgisi veya None.
        """
        key = f"{namespace}:{resource_type}"
        return self._limit_ranges.get(key)

    def set_priority_class(
        self,
        name: str,
        value: int,
        preemption: bool = True,
        description: str = "",
    ) -> dict[str, Any]:
        """Oncelik sinifi ayarlar.

        Args:
            name: Sinif adi.
            value: Oncelik degeri.
            preemption: Onalim aktif mi.
            description: Aciklama.

        Returns:
            Sinif bilgisi.
        """
        self._priority_classes[name] = {
            "name": name,
            "value": value,
            "preemption": preemption,
            "description": description,
        }

        return {
            "name": name,
            "value": value,
        }

    def get_priority_class(
        self,
        name: str,
    ) -> dict[str, Any] | None:
        """Oncelik sinifini getirir.

        Args:
            name: Sinif adi.

        Returns:
            Sinif bilgisi veya None.
        """
        return self._priority_classes.get(name)

    def get_usage(
        self,
        namespace: str,
    ) -> dict[str, Any]:
        """Kullanimi getirir.

        Args:
            namespace: Isim alani.

        Returns:
            Kullanim bilgisi.
        """
        return dict(
            self._usage.get(namespace, {}),
        )

    @property
    def quota_count(self) -> int:
        """Kota sayisi."""
        return len(self._quotas)

    @property
    def limit_range_count(self) -> int:
        """Limit araligi sayisi."""
        return len(self._limit_ranges)

    @property
    def priority_class_count(self) -> int:
        """Oncelik sinifi sayisi."""
        return len(self._priority_classes)
