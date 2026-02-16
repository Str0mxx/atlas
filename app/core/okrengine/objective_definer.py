"""ATLAS Hedef Tanımlayıcı.

OKR hedef tanımlama, SMART validasyon,
hiyerarşi yönetimi, sahiplik, zaman çizelgesi.
"""

import logging
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)


class ObjectiveDefiner:
    """Hedef tanımlayıcı.

    OKR hedefleri oluşturur, SMART kriterleriyle
    doğrular, hiyerarşi ve zaman çizelgesi belirler.

    Attributes:
        _objectives: Hedef kayıtları.
        _stats: İstatistikler.
    """

    def __init__(self) -> None:
        """Tanımlayıcıyı başlatır."""
        self._objectives: dict[
            str, dict
        ] = {}
        self._stats = {
            "objectives_created": 0,
        }
        logger.info(
            "ObjectiveDefiner "
            "baslatildi",
        )

    @property
    def objective_count(self) -> int:
        """Hedef sayısı."""
        return self._stats[
            "objectives_created"
        ]

    def create_objective(
        self,
        title: str,
        level: str = "company",
        owner: str = "",
        parent_id: str = "",
        timeline_months: int = 3,
    ) -> dict[str, Any]:
        """Hedef oluşturur.

        Args:
            title: Hedef başlığı.
            level: Seviye (company/department/team/individual).
            owner: Hedef sahibi.
            parent_id: Üst hedef ID.
            timeline_months: Zaman çizelgesi (ay).

        Returns:
            Hedef bilgisi.
        """
        oid = f"obj_{str(uuid4())[:8]}"

        self._objectives[oid] = {
            "title": title,
            "level": level,
            "owner": owner,
            "parent_id": parent_id,
            "timeline_months": timeline_months,
        }
        self._stats[
            "objectives_created"
        ] += 1

        logger.info(
            f"Hedef olusturuldu: {oid} - {title}",
        )

        return {
            "objective_id": oid,
            "title": title,
            "level": level,
            "owner": owner,
            "parent_id": parent_id,
            "timeline_months": timeline_months,
            "created": True,
        }

    def validate_smart(
        self,
        objective_id: str,
    ) -> dict[str, Any]:
        """SMART validasyon yapar.

        Args:
            objective_id: Hedef ID.

        Returns:
            Validasyon bilgisi.
        """
        if objective_id not in self._objectives:
            logger.warning(
                f"Hedef bulunamadi: {objective_id}",
            )
            return {
                "objective_id": objective_id,
                "specific": False,
                "measurable": False,
                "achievable": False,
                "relevant": False,
                "time_bound": False,
                "smart_score": 0,
                "valid": False,
            }

        obj = self._objectives[
            objective_id
        ]

        specific = len(obj["title"]) > 5
        measurable = (
            obj.get("parent_id", "") != ""
            or objective_id
            in self._objectives
        )
        achievable = True
        relevant = obj.get("level", "") != ""
        time_bound = (
            obj.get("timeline_months", 0) > 0
        )

        score = round(
            sum(
                [
                    specific,
                    measurable,
                    achievable,
                    relevant,
                    time_bound,
                ],
            )
            / 5
            * 100,
            1,
        )

        valid = score >= 60

        logger.info(
            f"SMART validasyon: {objective_id} - Skor: {score}",
        )

        return {
            "objective_id": objective_id,
            "specific": specific,
            "measurable": measurable,
            "achievable": achievable,
            "relevant": relevant,
            "time_bound": time_bound,
            "smart_score": score,
            "valid": valid,
        }

    def set_hierarchy(
        self,
        objective_id: str,
        parent_id: str = "",
    ) -> dict[str, Any]:
        """Hiyerarşi belirler.

        Args:
            objective_id: Hedef ID.
            parent_id: Üst hedef ID.

        Returns:
            Hiyerarşi bilgisi.
        """
        if objective_id not in self._objectives:
            logger.warning(
                f"Hedef bulunamadi: {objective_id}",
            )
            return {
                "objective_id": objective_id,
                "parent_id": parent_id,
                "depth": 0,
                "hierarchy_set": False,
            }

        self._objectives[objective_id][
            "parent_id"
        ] = parent_id

        obj = self._objectives[
            objective_id
        ]
        level = obj.get("level", "")

        depth_map = {
            "company": 0,
            "department": 1,
            "team": 2,
            "individual": 3,
        }
        depth = depth_map.get(level, 0)

        logger.info(
            f"Hiyerarsi belirlendi: {objective_id} -> {parent_id} (depth: {depth})",
        )

        return {
            "objective_id": objective_id,
            "parent_id": parent_id,
            "depth": depth,
            "hierarchy_set": True,
        }

    def assign_owner(
        self,
        objective_id: str,
        owner: str = "",
    ) -> dict[str, Any]:
        """Sahip atar.

        Args:
            objective_id: Hedef ID.
            owner: Hedef sahibi.

        Returns:
            Atama bilgisi.
        """
        if objective_id not in self._objectives:
            logger.warning(
                f"Hedef bulunamadi: {objective_id}",
            )
            return {
                "objective_id": objective_id,
                "owner": owner,
                "assigned": False,
            }

        self._objectives[objective_id][
            "owner"
        ] = owner

        logger.info(
            f"Sahip atandi: {objective_id} -> {owner}",
        )

        return {
            "objective_id": objective_id,
            "owner": owner,
            "assigned": True,
        }

    def set_timeline(
        self,
        objective_id: str,
        months: int = 3,
    ) -> dict[str, Any]:
        """Zaman çizelgesi belirler.

        Args:
            objective_id: Hedef ID.
            months: Ay sayısı.

        Returns:
            Zaman çizelgesi bilgisi.
        """
        if objective_id not in self._objectives:
            logger.warning(
                f"Hedef bulunamadi: {objective_id}",
            )
            return {
                "objective_id": objective_id,
                "months": months,
                "period": "",
                "timeline_set": False,
            }

        self._objectives[objective_id][
            "timeline_months"
        ] = months

        period = ""
        if months <= 3:
            period = "quarterly"
        elif months <= 6:
            period = "half_year"
        elif months <= 12:
            period = "annual"
        else:
            period = "multi_year"

        logger.info(
            f"Zaman cizelgesi belirlendi: {objective_id} - {months} ay ({period})",
        )

        return {
            "objective_id": objective_id,
            "months": months,
            "period": period,
            "timeline_set": True,
        }
