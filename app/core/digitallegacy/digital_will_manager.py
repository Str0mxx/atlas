"""
Dijital vasiyet yöneticisi modülü.

Vasiyet oluşturma, varlık dağıtımı,
talimat saklama, güncelleme takibi, yürütme planı.
"""

import logging
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)


class DigitalWillManager:
    """Dijital vasiyet yöneticisi.

    Attributes:
        _wills: Vasiyet kayıtları.
        _stats: İstatistikler.
    """

    def __init__(self) -> None:
        """Yöneticiyi başlatır."""
        self._wills: list[dict] = []
        self._stats: dict[str, int] = {
            "wills_created": 0,
        }
        logger.info(
            "DigitalWillManager baslatildi"
        )

    @property
    def will_count(self) -> int:
        """Vasiyet sayısı."""
        return len(self._wills)

    def create_will(
        self,
        title: str = "",
        description: str = "",
    ) -> dict[str, Any]:
        """Vasiyet oluşturur.

        Args:
            title: Başlık.
            description: Açıklama.

        Returns:
            Vasiyet bilgisi.
        """
        try:
            wid = f"wl_{uuid4()!s:.8}"

            record = {
                "will_id": wid,
                "title": title,
                "description": description,
                "status": "draft",
                "version": 1,
                "distributions": [],
                "instructions": [],
            }
            self._wills.append(record)
            self._stats["wills_created"] += 1

            return {
                "will_id": wid,
                "title": title,
                "status": "draft",
                "version": 1,
                "created": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "created": False,
                "error": str(e),
            }

    def distribute_assets(
        self,
        will_id: str = "",
        distributions: list[dict] | None = None,
    ) -> dict[str, Any]:
        """Varlıkları dağıtır.

        Args:
            will_id: Vasiyet ID.
            distributions: Dağıtım listesi.

        Returns:
            Dağıtım bilgisi.
        """
        try:
            will = None
            for w in self._wills:
                if w["will_id"] == will_id:
                    will = w
                    break

            if not will:
                return {
                    "distributed": False,
                    "error": "will_not_found",
                }

            items = distributions or []
            total_pct = sum(
                d.get("percentage", 0)
                for d in items
            )

            if total_pct > 100:
                return {
                    "distributed": False,
                    "error": "exceeds_100_percent",
                }

            will["distributions"] = items

            if total_pct == 100:
                coverage = "complete"
            elif total_pct >= 80:
                coverage = "mostly_covered"
            elif total_pct > 0:
                coverage = "partial"
            else:
                coverage = "empty"

            return {
                "will_id": will_id,
                "distribution_count": len(
                    items
                ),
                "total_pct": total_pct,
                "remaining_pct": 100 - total_pct,
                "coverage": coverage,
                "distributed": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "distributed": False,
                "error": str(e),
            }

    def store_instructions(
        self,
        will_id: str = "",
        instructions: list[str] | None = None,
    ) -> dict[str, Any]:
        """Talimat saklar.

        Args:
            will_id: Vasiyet ID.
            instructions: Talimat listesi.

        Returns:
            Saklama bilgisi.
        """
        try:
            will = None
            for w in self._wills:
                if w["will_id"] == will_id:
                    will = w
                    break

            if not will:
                return {
                    "stored": False,
                    "error": "will_not_found",
                }

            items = instructions or []
            numbered = []
            for i, inst in enumerate(items, 1):
                numbered.append({
                    "step": i,
                    "instruction": inst,
                })

            will["instructions"] = numbered

            return {
                "will_id": will_id,
                "instruction_count": len(
                    numbered
                ),
                "stored": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "stored": False,
                "error": str(e),
            }

    def update_will(
        self,
        will_id: str = "",
        changes: dict | None = None,
    ) -> dict[str, Any]:
        """Vasiyeti günceller.

        Args:
            will_id: Vasiyet ID.
            changes: Değişiklikler.

        Returns:
            Güncelleme bilgisi.
        """
        try:
            will = None
            for w in self._wills:
                if w["will_id"] == will_id:
                    will = w
                    break

            if not will:
                return {
                    "updated": False,
                    "error": "will_not_found",
                }

            updates = changes or {}
            old_version = will["version"]
            will["version"] = old_version + 1

            if "title" in updates:
                will["title"] = updates["title"]
            if "description" in updates:
                will["description"] = updates[
                    "description"
                ]

            will["status"] = "updated"

            return {
                "will_id": will_id,
                "old_version": old_version,
                "new_version": will["version"],
                "changes_applied": len(updates),
                "status": "updated",
                "updated": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "updated": False,
                "error": str(e),
            }

    def plan_execution(
        self,
        will_id: str = "",
    ) -> dict[str, Any]:
        """Yürütme planı oluşturur.

        Args:
            will_id: Vasiyet ID.

        Returns:
            Yürütme planı bilgisi.
        """
        try:
            will = None
            for w in self._wills:
                if w["will_id"] == will_id:
                    will = w
                    break

            if not will:
                return {
                    "planned": False,
                    "error": "will_not_found",
                }

            has_distributions = len(
                will["distributions"]
            ) > 0
            has_instructions = len(
                will["instructions"]
            ) > 0

            readiness_score = 0
            if has_distributions:
                readiness_score += 40
            if has_instructions:
                readiness_score += 30
            if will["version"] >= 2:
                readiness_score += 15
            if will["status"] != "draft":
                readiness_score += 15

            if readiness_score >= 80:
                readiness = "ready"
            elif readiness_score >= 50:
                readiness = "mostly_ready"
            elif readiness_score > 0:
                readiness = "in_progress"
            else:
                readiness = "not_started"

            return {
                "will_id": will_id,
                "title": will["title"],
                "version": will["version"],
                "distributions": len(
                    will["distributions"]
                ),
                "instructions": len(
                    will["instructions"]
                ),
                "readiness_score": readiness_score,
                "readiness": readiness,
                "planned": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "planned": False,
                "error": str(e),
            }
