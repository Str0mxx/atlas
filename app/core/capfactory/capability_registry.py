"""ATLAS Yetenek Kayıt Defteri modülü.

Yetenek kataloğu, versiyon takibi,
kullanım istatistikleri, kullanımdan kaldırma,
keşif.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class RuntimeCapabilityRegistry:
    """Yetenek kayıt defteri.

    Çalışma zamanı yeteneklerini kaydeder ve yönetir.

    Attributes:
        _capabilities: Yetenek kataloğu.
        _usage_stats: Kullanım istatistikleri.
    """

    def __init__(self) -> None:
        """Kayıt defterini başlatır."""
        self._capabilities: dict[
            str, dict[str, Any]
        ] = {}
        self._usage_stats: dict[
            str, dict[str, int]
        ] = {}
        self._counter = 0
        self._stats = {
            "registered": 0,
            "deprecated": 0,
            "total_usage": 0,
        }

        logger.info(
            "RuntimeCapabilityRegistry "
            "baslatildi",
        )

    def register(
        self,
        name: str,
        version: str = "1.0.0",
        description: str = "",
        tags: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Yetenek kaydeder.

        Args:
            name: Yetenek adı.
            version: Versiyon.
            description: Açıklama.
            tags: Etiketler.
            metadata: Ek veri.

        Returns:
            Kayıt bilgisi.
        """
        self._counter += 1
        cid = f"cap_{self._counter}"

        capability = {
            "capability_id": cid,
            "name": name,
            "version": version,
            "description": description,
            "tags": tags or [],
            "metadata": metadata or {},
            "status": "active",
            "versions": [version],
            "created_at": time.time(),
            "updated_at": time.time(),
        }
        self._capabilities[cid] = capability
        self._usage_stats[cid] = {
            "invocations": 0,
            "successes": 0,
            "failures": 0,
        }
        self._stats["registered"] += 1

        return {
            "capability_id": cid,
            "name": name,
            "version": version,
            "registered": True,
        }

    def update_version(
        self,
        capability_id: str,
        new_version: str,
    ) -> dict[str, Any]:
        """Versiyon günceller.

        Args:
            capability_id: Yetenek ID.
            new_version: Yeni versiyon.

        Returns:
            Güncelleme bilgisi.
        """
        cap = self._capabilities.get(capability_id)
        if not cap:
            return {
                "error": "capability_not_found",
            }

        old_version = cap["version"]
        cap["version"] = new_version
        cap["versions"].append(new_version)
        cap["updated_at"] = time.time()

        return {
            "capability_id": capability_id,
            "old_version": old_version,
            "new_version": new_version,
            "updated": True,
        }

    def record_usage(
        self,
        capability_id: str,
        success: bool = True,
    ) -> dict[str, Any]:
        """Kullanım kaydeder.

        Args:
            capability_id: Yetenek ID.
            success: Başarılı mı.

        Returns:
            Kayıt bilgisi.
        """
        stats = self._usage_stats.get(capability_id)
        if not stats:
            return {
                "error": "capability_not_found",
            }

        stats["invocations"] += 1
        if success:
            stats["successes"] += 1
        else:
            stats["failures"] += 1
        self._stats["total_usage"] += 1

        return {
            "capability_id": capability_id,
            "invocations": stats["invocations"],
            "success": success,
        }

    def get_usage_stats(
        self,
        capability_id: str,
    ) -> dict[str, Any]:
        """Kullanım istatistikleri getirir.

        Args:
            capability_id: Yetenek ID.

        Returns:
            İstatistik bilgisi.
        """
        stats = self._usage_stats.get(capability_id)
        if not stats:
            return {
                "error": "capability_not_found",
            }

        total = stats["invocations"]
        success_rate = (
            round(
                stats["successes"] / total * 100, 1,
            ) if total > 0 else 0.0
        )

        return {
            "capability_id": capability_id,
            **stats,
            "success_rate": success_rate,
        }

    def deprecate(
        self,
        capability_id: str,
        reason: str = "",
    ) -> dict[str, Any]:
        """Kullanımdan kaldırır.

        Args:
            capability_id: Yetenek ID.
            reason: Neden.

        Returns:
            Kaldırma bilgisi.
        """
        cap = self._capabilities.get(capability_id)
        if not cap:
            return {
                "error": "capability_not_found",
            }

        cap["status"] = "deprecated"
        cap["deprecated_at"] = time.time()
        cap["deprecation_reason"] = reason
        self._stats["deprecated"] += 1

        return {
            "capability_id": capability_id,
            "deprecated": True,
            "reason": reason,
        }

    def discover(
        self,
        query: str = "",
        tags: list[str] | None = None,
        active_only: bool = True,
    ) -> list[dict[str, Any]]:
        """Yetenek keşfeder.

        Args:
            query: Arama sorgusu.
            tags: Etiket filtresi.
            active_only: Sadece aktif.

        Returns:
            Yetenek listesi.
        """
        results = []
        query_lower = query.lower()

        for cap in self._capabilities.values():
            if active_only and cap[
                "status"
            ] != "active":
                continue

            if query_lower:
                name_match = (
                    query_lower
                    in cap["name"].lower()
                )
                desc_match = (
                    query_lower
                    in cap.get(
                        "description", "",
                    ).lower()
                )
                if not name_match and not desc_match:
                    continue

            if tags:
                cap_tags = set(cap.get("tags", []))
                if not set(tags) & cap_tags:
                    continue

            results.append(dict(cap))

        return results

    def get_capability(
        self,
        capability_id: str,
    ) -> dict[str, Any]:
        """Yetenek getirir.

        Args:
            capability_id: Yetenek ID.

        Returns:
            Yetenek bilgisi.
        """
        cap = self._capabilities.get(capability_id)
        if not cap:
            return {
                "error": "capability_not_found",
            }
        return dict(cap)

    def list_capabilities(
        self,
        status: str | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """Yetenekleri listeler.

        Args:
            status: Durum filtresi.
            limit: Maks kayıt.

        Returns:
            Yetenek listesi.
        """
        results = list(
            self._capabilities.values(),
        )
        if status:
            results = [
                c for c in results
                if c["status"] == status
            ]
        return results[:limit]

    @property
    def registered_count(self) -> int:
        """Kayıtlı yetenek sayısı."""
        return self._stats["registered"]

    @property
    def active_count(self) -> int:
        """Aktif yetenek sayısı."""
        return sum(
            1 for c in self._capabilities.values()
            if c["status"] == "active"
        )

    @property
    def deprecated_count(self) -> int:
        """Kaldırılan yetenek sayısı."""
        return self._stats["deprecated"]
