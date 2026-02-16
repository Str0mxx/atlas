"""
Finansal hedef takipçisi modülü.

Hedef belirleme, ilerleme takibi,
kilometre taşı kutlaması, projeksiyon
ve strateji ayarlama sağlar.
"""

import logging
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)


class PersonalFinancialGoalTracker:
    """Finansal hedef takipçisi.

    Finansal hedefler belirler, ilerleme
    takibi yapar ve projeksiyon sağlar.

    Attributes:
        _goals: Hedef kayıtları.
        _stats: İstatistikler.
    """

    def __init__(self) -> None:
        """Takipçiyi başlatır."""
        self._goals: list[dict] = []
        self._stats: dict[str, int] = {
            "goals_created": 0,
        }
        logger.info(
            "PersonalFinancialGoalTracker "
            "baslatildi"
        )

    @property
    def goal_count(self) -> int:
        """Hedef sayısı."""
        return len(self._goals)

    def set_goal(
        self,
        name: str = "Financial Goal",
        goal_type: str = "emergency_fund",
        target: float = 100000.0,
        deadline_months: int = 24,
    ) -> dict[str, Any]:
        """Finansal hedef belirler.

        Args:
            name: Hedef adı.
            goal_type: Hedef türü.
            target: Hedef tutar.
            deadline_months: Süre (ay).

        Returns:
            Hedef bilgisi.
        """
        try:
            gid = f"fg_{uuid4()!s:.8}"
            monthly_req = round(
                target
                / max(deadline_months, 1),
                2,
            )
            goal = {
                "goal_id": gid,
                "name": name,
                "goal_type": goal_type,
                "target": target,
                "current": 0.0,
                "deadline_months": (
                    deadline_months
                ),
                "monthly_required": (
                    monthly_req
                ),
            }
            self._goals.append(goal)
            self._stats[
                "goals_created"
            ] += 1

            return {
                "goal_id": gid,
                "name": name,
                "goal_type": goal_type,
                "target": target,
                "monthly_required": (
                    monthly_req
                ),
                "set": True,
            }

        except Exception as e:
            logger.error(
                f"Hedef belirleme "
                f"hatasi: {e}"
            )
            return {
                "goal_id": "",
                "name": name,
                "set": False,
                "error": str(e),
            }

    def update_progress(
        self,
        goal_id: str,
        amount: float = 0.0,
    ) -> dict[str, Any]:
        """İlerleme günceller.

        Args:
            goal_id: Hedef ID.
            amount: Eklenen tutar.

        Returns:
            İlerleme bilgisi.
        """
        try:
            for g in self._goals:
                if g["goal_id"] == goal_id:
                    g["current"] += amount
                    pct = round(
                        (
                            g["current"]
                            / max(
                                g["target"], 1
                            )
                        )
                        * 100,
                        1,
                    )

                    if pct >= 100:
                        status = "completed"
                    elif pct >= 75:
                        status = "almost_there"
                    elif pct >= 50:
                        status = "halfway"
                    elif pct >= 25:
                        status = "progressing"
                    else:
                        status = "starting"

                    return {
                        "goal_id": goal_id,
                        "current": round(
                            g["current"], 2
                        ),
                        "target": g[
                            "target"
                        ],
                        "progress_pct": pct,
                        "status": status,
                        "updated": True,
                    }

            return {
                "goal_id": goal_id,
                "updated": False,
                "error": "goal_not_found",
            }

        except Exception as e:
            logger.error(
                f"Ilerleme guncelleme "
                f"hatasi: {e}"
            )
            return {
                "goal_id": goal_id,
                "updated": False,
                "error": str(e),
            }

    def check_milestones(
        self,
        goal_id: str,
    ) -> dict[str, Any]:
        """Kilometre taşlarını kontrol eder.

        Args:
            goal_id: Hedef ID.

        Returns:
            Kilometre taşı bilgisi.
        """
        try:
            for g in self._goals:
                if g["goal_id"] == goal_id:
                    pct = (
                        g["current"]
                        / max(g["target"], 1)
                    ) * 100

                    milestones = [
                        25,
                        50,
                        75,
                        100,
                    ]
                    reached = [
                        m
                        for m in milestones
                        if pct >= m
                    ]
                    next_ms = (
                        min(
                            m
                            for m in milestones
                            if pct < m
                        )
                        if pct < 100
                        else None
                    )

                    return {
                        "goal_id": goal_id,
                        "progress_pct": round(
                            pct, 1
                        ),
                        "reached": reached,
                        "reached_count": len(
                            reached
                        ),
                        "next_milestone": (
                            next_ms
                        ),
                        "checked": True,
                    }

            return {
                "goal_id": goal_id,
                "checked": False,
                "error": "goal_not_found",
            }

        except Exception as e:
            logger.error(
                f"Kilometre tasi "
                f"hatasi: {e}"
            )
            return {
                "goal_id": goal_id,
                "checked": False,
                "error": str(e),
            }

    def project_completion(
        self,
        goal_id: str,
        monthly_contribution: float = 0.0,
    ) -> dict[str, Any]:
        """Tamamlanma projeksiyonu yapar.

        Args:
            goal_id: Hedef ID.
            monthly_contribution: Aylık katkı.

        Returns:
            Projeksiyon bilgisi.
        """
        try:
            for g in self._goals:
                if g["goal_id"] == goal_id:
                    remaining = (
                        g["target"]
                        - g["current"]
                    )
                    if (
                        monthly_contribution
                        > 0
                    ):
                        months = round(
                            remaining
                            / monthly_contribution,
                            1,
                        )
                    else:
                        months = float("inf")

                    on_track = (
                        months
                        <= g[
                            "deadline_months"
                        ]
                    )

                    return {
                        "goal_id": goal_id,
                        "remaining": round(
                            remaining, 2
                        ),
                        "months_needed": (
                            months
                        ),
                        "on_track": on_track,
                        "projected": True,
                    }

            return {
                "goal_id": goal_id,
                "projected": False,
                "error": "goal_not_found",
            }

        except Exception as e:
            logger.error(
                f"Projeksiyon hatasi: {e}"
            )
            return {
                "goal_id": goal_id,
                "projected": False,
                "error": str(e),
            }

    def adjust_strategy(
        self,
        goal_id: str,
        new_monthly: float = 0.0,
    ) -> dict[str, Any]:
        """Strateji ayarlar.

        Args:
            goal_id: Hedef ID.
            new_monthly: Yeni aylık katkı.

        Returns:
            Ayarlama sonucu.
        """
        try:
            for g in self._goals:
                if g["goal_id"] == goal_id:
                    old = g[
                        "monthly_required"
                    ]
                    g["monthly_required"] = (
                        new_monthly
                    )
                    change = round(
                        new_monthly - old, 2
                    )

                    remaining = (
                        g["target"]
                        - g["current"]
                    )
                    new_months = round(
                        remaining
                        / max(new_monthly, 1),
                        1,
                    )

                    return {
                        "goal_id": goal_id,
                        "old_monthly": old,
                        "new_monthly": (
                            new_monthly
                        ),
                        "change": change,
                        "new_timeline_months": (
                            new_months
                        ),
                        "adjusted": True,
                    }

            return {
                "goal_id": goal_id,
                "adjusted": False,
                "error": "goal_not_found",
            }

        except Exception as e:
            logger.error(
                f"Strateji ayarlama "
                f"hatasi: {e}"
            )
            return {
                "goal_id": goal_id,
                "adjusted": False,
                "error": str(e),
            }
