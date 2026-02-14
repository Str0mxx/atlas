"""ATLAS Girisim Baslatici modulu.

Hedefi goreve donusturme, kaynak tahsisi,
zaman cizelgesi olusturma, basari metrikleri
ve izleme kurulumu.
"""

import logging
from datetime import datetime, timezone
from typing import Any

from app.models.goal_pursuit import (
    GoalDefinition,
    GoalState,
    Initiative,
    InitiativeState,
)

logger = logging.getLogger(__name__)


class InitiativeLauncher:
    """Girisim baslatici.

    Onaylanan hedefleri calistirilabilir
    girisimlere donusturur.

    Attributes:
        _initiatives: Girisimler.
        _resource_pool: Kaynak havuzu.
        _monitoring: Izleme kayitlari.
    """

    def __init__(self) -> None:
        """Girisim baslaticiyi baslatir."""
        self._initiatives: dict[str, Initiative] = {}
        self._resource_pool: dict[str, float] = {}
        self._monitoring: dict[str, dict[str, Any]] = {}
        self._timeline_templates: dict[str, list[dict[str, Any]]] = {}

        logger.info("InitiativeLauncher baslatildi")

    def create_initiative(
        self,
        goal: GoalDefinition,
        resources: list[str] | None = None,
        milestones: list[str] | None = None,
        timeline_days: int = 30,
    ) -> Initiative:
        """Hedeften girisim olusturur.

        Args:
            goal: Hedef tanimi.
            resources: Atanacak kaynaklar.
            milestones: Kilometre taslari.
            timeline_days: Zaman cizelgesi (gun).

        Returns:
            Initiative nesnesi.
        """
        initiative = Initiative(
            goal_id=goal.goal_id,
            name=goal.title,
            resources=resources or [],
            milestones=milestones or [],
            timeline_days=timeline_days,
            metadata={
                "priority": goal.priority.value,
                "estimated_value": goal.estimated_value,
            },
        )
        self._initiatives[initiative.initiative_id] = initiative

        logger.info(
            "Girisim olusturuldu: %s (%s)",
            initiative.name, initiative.initiative_id,
        )
        return initiative

    def launch(self, initiative_id: str) -> dict[str, Any]:
        """Girisimi baslatir.

        Args:
            initiative_id: Girisim ID.

        Returns:
            Baslatma sonucu.
        """
        initiative = self._initiatives.get(initiative_id)
        if not initiative:
            return {"success": False, "reason": "Girisim bulunamadi"}

        if initiative.state != InitiativeState.PLANNED:
            return {
                "success": False,
                "reason": f"Gecersiz durum: {initiative.state.value}",
            }

        initiative.state = InitiativeState.LAUNCHING
        initiative.launched_at = datetime.now(timezone.utc)

        # Izleme kur
        self._monitoring[initiative_id] = {
            "launched_at": initiative.launched_at.isoformat(),
            "checkpoints": [],
            "alerts": [],
        }

        initiative.state = InitiativeState.RUNNING

        logger.info("Girisim baslatildi: %s", initiative.name)
        return {
            "success": True,
            "initiative_id": initiative_id,
            "state": initiative.state.value,
        }

    def allocate_resources(
        self,
        initiative_id: str,
        resources: dict[str, float],
    ) -> dict[str, Any]:
        """Kaynak tahsis eder.

        Args:
            initiative_id: Girisim ID.
            resources: Kaynak -> miktar eslesmesi.

        Returns:
            Tahsis sonucu.
        """
        initiative = self._initiatives.get(initiative_id)
        if not initiative:
            return {"success": False, "reason": "Girisim bulunamadi"}

        allocated = {}
        insufficient = {}

        for resource, amount in resources.items():
            available = self._resource_pool.get(resource, 0.0)
            if available >= amount:
                self._resource_pool[resource] = available - amount
                allocated[resource] = amount
                if resource not in initiative.resources:
                    initiative.resources.append(resource)
            else:
                insufficient[resource] = amount - available

        return {
            "success": len(insufficient) == 0,
            "allocated": allocated,
            "insufficient": insufficient,
        }

    def set_resource_pool(
        self,
        resources: dict[str, float],
    ) -> None:
        """Kaynak havuzunu ayarlar.

        Args:
            resources: Kaynak -> miktar eslesmesi.
        """
        self._resource_pool.update(resources)

    def set_success_metrics(
        self,
        initiative_id: str,
        metrics: dict[str, float],
    ) -> bool:
        """Basari metriklerini ayarlar.

        Args:
            initiative_id: Girisim ID.
            metrics: Metrik -> hedef deger.

        Returns:
            Basarili ise True.
        """
        initiative = self._initiatives.get(initiative_id)
        if not initiative:
            return False

        initiative.success_metrics.update(metrics)
        return True

    def add_milestone(
        self,
        initiative_id: str,
        milestone: str,
    ) -> bool:
        """Kilometre tasi ekler.

        Args:
            initiative_id: Girisim ID.
            milestone: Kilometre tasi.

        Returns:
            Basarili ise True.
        """
        initiative = self._initiatives.get(initiative_id)
        if not initiative:
            return False

        initiative.milestones.append(milestone)
        return True

    def update_progress(
        self,
        initiative_id: str,
        progress: float,
    ) -> bool:
        """Ilerleme gunceller.

        Args:
            initiative_id: Girisim ID.
            progress: Ilerleme (0-1).

        Returns:
            Basarili ise True.
        """
        initiative = self._initiatives.get(initiative_id)
        if not initiative:
            return False

        initiative.progress = max(0.0, min(1.0, progress))

        # Checkpoint kaydet
        monitoring = self._monitoring.get(initiative_id, {})
        checkpoints = monitoring.get("checkpoints", [])
        checkpoints.append({
            "progress": initiative.progress,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

        return True

    def complete_initiative(
        self,
        initiative_id: str,
    ) -> bool:
        """Girisimi tamamlar.

        Args:
            initiative_id: Girisim ID.

        Returns:
            Basarili ise True.
        """
        initiative = self._initiatives.get(initiative_id)
        if not initiative:
            return False

        initiative.state = InitiativeState.COMPLETED
        initiative.progress = 1.0
        initiative.completed_at = datetime.now(timezone.utc)

        logger.info("Girisim tamamlandi: %s", initiative.name)
        return True

    def abort_initiative(
        self,
        initiative_id: str,
        reason: str = "",
    ) -> bool:
        """Girisimi iptal eder.

        Args:
            initiative_id: Girisim ID.
            reason: Iptal nedeni.

        Returns:
            Basarili ise True.
        """
        initiative = self._initiatives.get(initiative_id)
        if not initiative:
            return False

        initiative.state = InitiativeState.ABORTED
        initiative.metadata["abort_reason"] = reason

        logger.info("Girisim iptal edildi: %s", initiative.name)
        return True

    def get_initiative(
        self,
        initiative_id: str,
    ) -> Initiative | None:
        """Girisim getirir.

        Args:
            initiative_id: Girisim ID.

        Returns:
            Initiative veya None.
        """
        return self._initiatives.get(initiative_id)

    def get_by_goal(self, goal_id: str) -> list[Initiative]:
        """Hedefe ait girisimleri getirir.

        Args:
            goal_id: Hedef ID.

        Returns:
            Girisim listesi.
        """
        return [
            i for i in self._initiatives.values()
            if i.goal_id == goal_id
        ]

    def get_active(self) -> list[Initiative]:
        """Aktif girisimleri getirir.

        Returns:
            Aktif girisim listesi.
        """
        return [
            i for i in self._initiatives.values()
            if i.state in (
                InitiativeState.LAUNCHING,
                InitiativeState.RUNNING,
                InitiativeState.MONITORING,
            )
        ]

    @property
    def total_initiatives(self) -> int:
        """Toplam girisim sayisi."""
        return len(self._initiatives)

    @property
    def active_count(self) -> int:
        """Aktif girisim sayisi."""
        return len(self.get_active())

    @property
    def completed_count(self) -> int:
        """Tamamlanan girisim sayisi."""
        return sum(
            1 for i in self._initiatives.values()
            if i.state == InitiativeState.COMPLETED
        )
