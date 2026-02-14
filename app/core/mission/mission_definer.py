"""ATLAS Gorev Tanimlayici modulu.

High-level goal parsing, basari kriterleri,
kisitlama, zaman cizgisi ve butce yonetimi.
"""

import logging
from typing import Any

from app.models.mission import MissionDefinition, MissionState

logger = logging.getLogger(__name__)


class MissionDefiner:
    """Gorev tanimlayici.

    Gorevleri tanimlar, basari kriterlerini belirler,
    kisitlamalari ve butceleri yonetir.

    Attributes:
        _missions: Gorev tanimlari.
        _templates: Gorev sablonlari.
    """

    def __init__(self) -> None:
        """Gorev tanimlayiciyi baslatir."""
        self._missions: dict[str, MissionDefinition] = {}
        self._templates: dict[str, dict[str, Any]] = {}

        logger.info("MissionDefiner baslatildi")

    def define_mission(
        self,
        name: str,
        goal: str,
        description: str = "",
        priority: int = 5,
        timeline_hours: float = 0.0,
        budget: float = 0.0,
        tags: list[str] | None = None,
    ) -> MissionDefinition:
        """Gorev tanimlar.

        Args:
            name: Gorev adi.
            goal: Ana hedef.
            description: Aciklama.
            priority: Oncelik (1-10).
            timeline_hours: Zaman siniri (saat).
            budget: Butce.
            tags: Etiketler.

        Returns:
            MissionDefinition nesnesi.
        """
        mission = MissionDefinition(
            name=name,
            goal=goal,
            description=description,
            priority=max(1, min(10, priority)),
            timeline_hours=timeline_hours,
            budget=budget,
            tags=tags or [],
        )
        self._missions[mission.mission_id] = mission

        logger.info("Gorev tanimlandi: %s (%s)", name, mission.mission_id)
        return mission

    def define_from_template(
        self,
        template_name: str,
        name: str,
        overrides: dict[str, Any] | None = None,
    ) -> MissionDefinition | None:
        """Sablondan gorev tanimlar.

        Args:
            template_name: Sablon adi.
            name: Gorev adi.
            overrides: Ustune yazilacak alanlar.

        Returns:
            MissionDefinition veya None.
        """
        template = self._templates.get(template_name)
        if not template:
            return None

        params = dict(template)
        params["name"] = name
        if overrides:
            params.update(overrides)

        return self.define_mission(**params)

    def set_success_criteria(
        self,
        mission_id: str,
        criteria: list[str],
    ) -> bool:
        """Basari kriterlerini belirler.

        Args:
            mission_id: Gorev ID.
            criteria: Kriter listesi.

        Returns:
            Basarili ise True.
        """
        mission = self._missions.get(mission_id)
        if not mission:
            return False

        mission.success_criteria = criteria
        return True

    def set_constraints(
        self,
        mission_id: str,
        constraints: list[str],
    ) -> bool:
        """Kisitlamalari belirler.

        Args:
            mission_id: Gorev ID.
            constraints: Kisitlama listesi.

        Returns:
            Basarili ise True.
        """
        mission = self._missions.get(mission_id)
        if not mission:
            return False

        mission.constraints = constraints
        return True

    def set_timeline(
        self,
        mission_id: str,
        hours: float,
    ) -> bool:
        """Zaman cizgisini belirler.

        Args:
            mission_id: Gorev ID.
            hours: Saat cinsinden sure.

        Returns:
            Basarili ise True.
        """
        mission = self._missions.get(mission_id)
        if not mission or hours <= 0:
            return False

        mission.timeline_hours = hours
        return True

    def set_budget(
        self,
        mission_id: str,
        budget: float,
    ) -> bool:
        """Butceyi belirler.

        Args:
            mission_id: Gorev ID.
            budget: Butce miktari.

        Returns:
            Basarili ise True.
        """
        mission = self._missions.get(mission_id)
        if not mission or budget < 0:
            return False

        mission.budget = budget
        return True

    def spend_budget(
        self,
        mission_id: str,
        amount: float,
    ) -> bool:
        """Butceden harcar.

        Args:
            mission_id: Gorev ID.
            amount: Harcama miktari.

        Returns:
            Basarili ise True.
        """
        mission = self._missions.get(mission_id)
        if not mission or amount <= 0:
            return False

        if mission.budget > 0 and mission.budget_used + amount > mission.budget:
            return False

        mission.budget_used += amount
        return True

    def register_template(
        self,
        template_name: str,
        goal: str,
        priority: int = 5,
        timeline_hours: float = 0.0,
        budget: float = 0.0,
    ) -> None:
        """Sablon kaydeder.

        Args:
            template_name: Sablon adi.
            goal: Hedef.
            priority: Oncelik.
            timeline_hours: Zaman.
            budget: Butce.
        """
        self._templates[template_name] = {
            "goal": goal,
            "priority": priority,
            "timeline_hours": timeline_hours,
            "budget": budget,
        }

    def activate_mission(self, mission_id: str) -> bool:
        """Gorevi aktiflestirir.

        Args:
            mission_id: Gorev ID.

        Returns:
            Basarili ise True.
        """
        mission = self._missions.get(mission_id)
        if not mission or mission.state not in (
            MissionState.DRAFT, MissionState.PLANNING,
        ):
            return False

        mission.state = MissionState.PLANNING
        return True

    def get_mission(self, mission_id: str) -> MissionDefinition | None:
        """Gorevi getirir.

        Args:
            mission_id: Gorev ID.

        Returns:
            MissionDefinition veya None.
        """
        return self._missions.get(mission_id)

    def get_all_missions(self) -> list[MissionDefinition]:
        """Tum gorevleri getirir.

        Returns:
            Gorev listesi.
        """
        return list(self._missions.values())

    def get_budget_status(self, mission_id: str) -> dict[str, float]:
        """Butce durumunu getirir.

        Args:
            mission_id: Gorev ID.

        Returns:
            Butce bilgileri.
        """
        mission = self._missions.get(mission_id)
        if not mission:
            return {}

        remaining = mission.budget - mission.budget_used if mission.budget > 0 else 0
        usage_pct = (
            mission.budget_used / mission.budget * 100
            if mission.budget > 0 else 0.0
        )

        return {
            "budget": mission.budget,
            "used": mission.budget_used,
            "remaining": remaining,
            "usage_percent": round(usage_pct, 1),
        }

    @property
    def total_missions(self) -> int:
        """Toplam gorev sayisi."""
        return len(self._missions)

    @property
    def template_count(self) -> int:
        """Sablon sayisi."""
        return len(self._templates)
