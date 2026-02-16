"""
Tasarruf danışmanı modülü.

Tasarruf hedefleri, öneriler, otomatik
tasarruf kuralları, ilerleme takibi
ve optimizasyon sağlar.
"""

import logging
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)


class SavingsAdvisor:
    """Tasarruf danışmanı.

    Tasarruf hedefleri belirler, öneriler
    sunar ve otomatik tasarruf yönetir.

    Attributes:
        _goals: Tasarruf hedefleri.
        _stats: İstatistikler.
    """

    def __init__(self) -> None:
        """Danışmanı başlatır."""
        self._goals: list[dict] = []
        self._rules: list[dict] = []
        self._stats: dict[str, int] = {
            "goals_created": 0,
        }
        logger.info(
            "SavingsAdvisor baslatildi"
        )

    @property
    def goal_count(self) -> int:
        """Tasarruf hedefi sayısı."""
        return len(self._goals)

    def create_goal(
        self,
        name: str = "Emergency Fund",
        target: float = 50000.0,
        monthly_save: float = 5000.0,
    ) -> dict[str, Any]:
        """Tasarruf hedefi oluşturur.

        Args:
            name: Hedef adı.
            target: Hedef tutar.
            monthly_save: Aylık tasarruf.

        Returns:
            Hedef bilgisi.
        """
        try:
            gid = f"sav_{uuid4()!s:.8}"
            months = round(
                target
                / max(monthly_save, 1),
                1,
            )
            goal = {
                "goal_id": gid,
                "name": name,
                "target": target,
                "saved": 0.0,
                "monthly_save": monthly_save,
            }
            self._goals.append(goal)
            self._stats[
                "goals_created"
            ] += 1

            return {
                "goal_id": gid,
                "name": name,
                "target": target,
                "monthly_save": monthly_save,
                "months_to_goal": months,
                "created": True,
            }

        except Exception as e:
            logger.error(
                f"Hedef olusturma "
                f"hatasi: {e}"
            )
            return {
                "goal_id": "",
                "name": name,
                "created": False,
                "error": str(e),
            }

    def recommend_savings(
        self,
        income: float = 0.0,
        expenses: float = 0.0,
    ) -> dict[str, Any]:
        """Tasarruf önerisi sunar.

        Args:
            income: Gelir.
            expenses: Gider.

        Returns:
            Tasarruf önerisi.
        """
        try:
            surplus = round(
                income - expenses, 2
            )
            rate = round(
                (surplus / max(income, 1))
                * 100,
                1,
            )

            tips: list[str] = []
            if rate < 10:
                tips.append(
                    "reduce_discretionary"
                )
            if rate < 20:
                tips.append(
                    "target_20pct_savings"
                )
            if rate >= 30:
                tips.append(
                    "consider_investing"
                )
            if not tips:
                tips.append(
                    "good_savings_rate"
                )

            recommended = round(
                income * 0.2, 2
            )

            return {
                "income": income,
                "expenses": expenses,
                "surplus": surplus,
                "savings_rate": rate,
                "recommended_save": (
                    recommended
                ),
                "tips": tips,
                "recommended": True,
            }

        except Exception as e:
            logger.error(
                f"Tasarruf onerisi "
                f"hatasi: {e}"
            )
            return {
                "income": income,
                "expenses": expenses,
                "surplus": 0.0,
                "savings_rate": 0.0,
                "tips": [],
                "recommended": False,
                "error": str(e),
            }

    def add_auto_rule(
        self,
        rule_type: str = "percentage",
        value: float = 10.0,
        source: str = "income",
    ) -> dict[str, Any]:
        """Otomatik tasarruf kuralı ekler.

        Args:
            rule_type: Kural türü.
            value: Değer.
            source: Kaynak.

        Returns:
            Kural bilgisi.
        """
        try:
            rid = f"rule_{uuid4()!s:.8}"
            rule = {
                "rule_id": rid,
                "rule_type": rule_type,
                "value": value,
                "source": source,
                "active": True,
            }
            self._rules.append(rule)

            return {
                "rule_id": rid,
                "rule_type": rule_type,
                "value": value,
                "source": source,
                "total_rules": len(
                    self._rules
                ),
                "added": True,
            }

        except Exception as e:
            logger.error(
                f"Kural ekleme hatasi: {e}"
            )
            return {
                "rule_id": "",
                "added": False,
                "error": str(e),
            }

    def track_progress(
        self,
        goal_id: str,
        amount: float = 0.0,
    ) -> dict[str, Any]:
        """Tasarruf ilerlemesini takip eder.

        Args:
            goal_id: Hedef ID.
            amount: Eklenen tutar.

        Returns:
            İlerleme bilgisi.
        """
        try:
            for g in self._goals:
                if g["goal_id"] == goal_id:
                    g["saved"] += amount
                    pct = round(
                        (
                            g["saved"]
                            / max(
                                g["target"], 1
                            )
                        )
                        * 100,
                        1,
                    )
                    remaining = round(
                        g["target"]
                        - g["saved"],
                        2,
                    )

                    return {
                        "goal_id": goal_id,
                        "saved": round(
                            g["saved"], 2
                        ),
                        "target": g[
                            "target"
                        ],
                        "progress_pct": pct,
                        "remaining": (
                            remaining
                        ),
                        "tracked": True,
                    }

            return {
                "goal_id": goal_id,
                "tracked": False,
                "error": "goal_not_found",
            }

        except Exception as e:
            logger.error(
                f"Ilerleme takip "
                f"hatasi: {e}"
            )
            return {
                "goal_id": goal_id,
                "tracked": False,
                "error": str(e),
            }

    def optimize_savings(
        self,
        goals: list[dict[str, Any]]
        | None = None,
        available: float = 10000.0,
    ) -> dict[str, Any]:
        """Tasarrufu optimize eder.

        Args:
            goals: Hedef listesi.
            available: Mevcut tutar.

        Returns:
            Optimizasyon sonucu.
        """
        try:
            if goals is None:
                goals = []

            allocations: list[
                dict[str, Any]
            ] = []
            remaining = available

            sorted_goals = sorted(
                goals,
                key=lambda g: g.get(
                    "priority", 5
                ),
            )

            for g in sorted_goals:
                need = g.get("target", 0) - (
                    g.get("saved", 0)
                )
                alloc = min(
                    max(need, 0), remaining
                )
                allocations.append(
                    {
                        "name": g.get(
                            "name", "unknown"
                        ),
                        "allocated": round(
                            alloc, 2
                        ),
                    }
                )
                remaining -= alloc

            return {
                "available": available,
                "allocated_count": len(
                    allocations
                ),
                "allocations": allocations,
                "unallocated": round(
                    remaining, 2
                ),
                "optimized": True,
            }

        except Exception as e:
            logger.error(
                f"Optimizasyon hatasi: {e}"
            )
            return {
                "available": available,
                "allocated_count": 0,
                "allocations": [],
                "unallocated": available,
                "optimized": False,
                "error": str(e),
            }
