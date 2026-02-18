"""
Sistem durum haritası modülü.

Tüm sistemlerin genel görünümü,
durum göstergeleri, bağımlılık haritalama,
hızlı navigasyon, detay desteği.
"""

import logging
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)


class SystemStatusMap:
    """Sistem durum haritası.

    Attributes:
        _systems: Kayıtlı sistemler.
        _dependencies: Bağımlılık haritası.
        _stats: İstatistikler.
    """

    def __init__(self) -> None:
        """Haritayı başlatır."""
        self._systems: list[dict] = []
        self._dependencies: list[dict] = []
        self._stats: dict[str, int] = {
            "systems_registered": 0,
            "checks_performed": 0,
        }
        logger.info(
            "SystemStatusMap baslatildi"
        )

    @property
    def system_count(self) -> int:
        """Sistem sayısı."""
        return len(self._systems)

    def register_system(
        self,
        name: str = "",
        category: str = "core",
        components: list[str] | None = None,
    ) -> dict[str, Any]:
        """Sistem kaydeder.

        Args:
            name: Sistem adı.
            category: Kategori.
            components: Bileşenler.

        Returns:
            Kayıt bilgisi.
        """
        try:
            sid = f"sys_{uuid4()!s:.8}"
            comps = components or []

            record = {
                "system_id": sid,
                "name": name,
                "category": category,
                "components": comps,
                "status": "healthy",
                "health_score": 100.0,
            }
            self._systems.append(record)
            self._stats[
                "systems_registered"
            ] += 1

            return {
                "system_id": sid,
                "name": name,
                "category": category,
                "component_count": len(comps),
                "registered": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "registered": False,
                "error": str(e),
            }

    def get_overview(
        self,
    ) -> dict[str, Any]:
        """Tüm sistemlerin genel görünümü.

        Returns:
            Genel görünüm bilgisi.
        """
        try:
            healthy = sum(
                1 for s in self._systems
                if s["status"] == "healthy"
            )
            degraded = sum(
                1 for s in self._systems
                if s["status"] == "degraded"
            )
            down = sum(
                1 for s in self._systems
                if s["status"] == "down"
            )

            total = len(self._systems)
            overall_health = (
                (healthy / total * 100.0)
                if total > 0
                else 0.0
            )

            if overall_health >= 90:
                overall_status = "healthy"
            elif overall_health >= 70:
                overall_status = "degraded"
            else:
                overall_status = "critical"

            return {
                "total_systems": total,
                "healthy": healthy,
                "degraded": degraded,
                "down": down,
                "overall_health": round(
                    overall_health, 1
                ),
                "overall_status": overall_status,
                "retrieved": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "retrieved": False,
                "error": str(e),
            }

    def update_status(
        self,
        system_id: str = "",
        status: str = "healthy",
        health_score: float = 100.0,
        details: str = "",
    ) -> dict[str, Any]:
        """Sistem durumunu günceller.

        Args:
            system_id: Sistem ID.
            status: Durum.
            health_score: Sağlık puanı.
            details: Detaylar.

        Returns:
            Güncelleme bilgisi.
        """
        try:
            system = None
            for s in self._systems:
                if s["system_id"] == system_id:
                    system = s
                    break

            if not system:
                return {
                    "updated": False,
                    "error": "system_not_found",
                }

            prev_status = system["status"]
            system["status"] = status
            system["health_score"] = health_score
            system["details"] = details

            changed = prev_status != status

            return {
                "system_id": system_id,
                "status": status,
                "health_score": health_score,
                "previous_status": prev_status,
                "status_changed": changed,
                "updated": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "updated": False,
                "error": str(e),
            }

    def map_dependency(
        self,
        source_id: str = "",
        target_id: str = "",
        dependency_type: str = "requires",
    ) -> dict[str, Any]:
        """Bağımlılık haritalar.

        Args:
            source_id: Kaynak sistem ID.
            target_id: Hedef sistem ID.
            dependency_type: Bağımlılık türü.

        Returns:
            Haritalama bilgisi.
        """
        try:
            source = None
            target = None
            for s in self._systems:
                if s["system_id"] == source_id:
                    source = s
                if s["system_id"] == target_id:
                    target = s

            if not source or not target:
                return {
                    "mapped": False,
                    "error": "system_not_found",
                }

            dep = {
                "source_id": source_id,
                "target_id": target_id,
                "source_name": source["name"],
                "target_name": target["name"],
                "type": dependency_type,
            }
            self._dependencies.append(dep)

            return {
                "source_id": source_id,
                "target_id": target_id,
                "dependency_type": dependency_type,
                "total_deps": len(
                    self._dependencies
                ),
                "mapped": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "mapped": False,
                "error": str(e),
            }

    def drill_down(
        self,
        system_id: str = "",
    ) -> dict[str, Any]:
        """Sistem detayına iner.

        Args:
            system_id: Sistem ID.

        Returns:
            Detay bilgisi.
        """
        try:
            system = None
            for s in self._systems:
                if s["system_id"] == system_id:
                    system = s
                    break

            if not system:
                return {
                    "drilled": False,
                    "error": "system_not_found",
                }

            deps_out = [
                d for d in self._dependencies
                if d["source_id"] == system_id
            ]
            deps_in = [
                d for d in self._dependencies
                if d["target_id"] == system_id
            ]

            return {
                "system_id": system_id,
                "name": system["name"],
                "category": system["category"],
                "status": system["status"],
                "health_score": system[
                    "health_score"
                ],
                "components": system[
                    "components"
                ],
                "depends_on": len(deps_out),
                "depended_by": len(deps_in),
                "drilled": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "drilled": False,
                "error": str(e),
            }

    def navigate(
        self,
        category: str = "",
        status_filter: str = "",
    ) -> dict[str, Any]:
        """Hızlı navigasyon.

        Args:
            category: Kategori filtresi.
            status_filter: Durum filtresi.

        Returns:
            Navigasyon sonucu.
        """
        try:
            filtered = self._systems
            if category:
                filtered = [
                    s for s in filtered
                    if s["category"] == category
                ]
            if status_filter:
                filtered = [
                    s for s in filtered
                    if s["status"] == status_filter
                ]

            items = [
                {
                    "system_id": s["system_id"],
                    "name": s["name"],
                    "category": s["category"],
                    "status": s["status"],
                    "health_score": s[
                        "health_score"
                    ],
                }
                for s in filtered
            ]

            return {
                "results": items,
                "count": len(items),
                "category_filter": category,
                "status_filter": status_filter,
                "navigated": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "navigated": False,
                "error": str(e),
            }
