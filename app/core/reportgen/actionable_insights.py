"""ATLAS Aksiyona Dönüşen İçgörüler modülü.

İçgörü çıkarma, aksiyon önerisi,
sonraki adımlar, sahip atama,
son tarih önerisi.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class ActionableInsights:
    """Aksiyon içgörü üretici.

    Veriden aksiyona dönüşebilecek
    içgörüler çıkarır.

    Attributes:
        _insights: İçgörü geçmişi.
    """

    def __init__(self) -> None:
        """Üreticiyi başlatır."""
        self._insights: list[
            dict[str, Any]
        ] = []
        self._counter = 0
        self._stats = {
            "insights_extracted": 0,
            "actions_recommended": 0,
            "owners_assigned": 0,
            "deadlines_set": 0,
        }

        logger.info(
            "ActionableInsights baslatildi",
        )

    def extract_insights(
        self,
        data: dict[str, Any],
        context: str = "",
    ) -> dict[str, Any]:
        """İçgörü çıkarır.

        Args:
            data: Kaynak veri.
            context: Bağlam.

        Returns:
            İçgörü bilgisi.
        """
        insights = []

        for key, value in data.items():
            self._counter += 1
            iid = f"ins_{self._counter}"

            insight = {
                "insight_id": iid,
                "type": "observation",
                "metric": key,
                "value": value,
                "description": (
                    f"{key} = {value}"
                ),
                "context": context,
                "priority": "medium",
                "created_at": time.time(),
            }

            # Basit öncelik mantığı
            if isinstance(value, (int, float)):
                if value > 80:
                    insight["priority"] = "high"
                    insight["type"] = (
                        "opportunity"
                    )
                elif value < 20:
                    insight["priority"] = "high"
                    insight["type"] = "risk"

            insights.append(insight)
            self._insights.append(insight)
            self._stats[
                "insights_extracted"
            ] += 1

        return {
            "insights": insights,
            "count": len(insights),
            "context": context,
        }

    def recommend_actions(
        self,
        insights: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Aksiyon önerir.

        Args:
            insights: İçgörü listesi.

        Returns:
            Öneri bilgisi.
        """
        recommendations = []
        for insight in insights:
            rec = {
                "insight_id": insight.get(
                    "insight_id", "",
                ),
                "type": insight.get(
                    "type", "observation",
                ),
                "recommendation": (
                    self._generate_recommendation(
                        insight,
                    )
                ),
                "priority": insight.get(
                    "priority", "medium",
                ),
                "effort": "medium",
            }
            recommendations.append(rec)
            self._stats[
                "actions_recommended"
            ] += 1

        return {
            "recommendations": recommendations,
            "count": len(recommendations),
        }

    def _generate_recommendation(
        self,
        insight: dict[str, Any],
    ) -> str:
        """Öneri üretir."""
        itype = insight.get("type", "")
        metric = insight.get("metric", "")

        if itype == "opportunity":
            return (
                f"Leverage {metric} "
                f"for growth"
            )
        if itype == "risk":
            return (
                f"Address {metric} "
                f"immediately"
            )
        return f"Monitor {metric}"

    def suggest_next_steps(
        self,
        actions: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Sonraki adımları önerir.

        Args:
            actions: Aksiyon listesi.

        Returns:
            Adım bilgisi.
        """
        steps = []
        for i, action in enumerate(actions):
            step = {
                "step": i + 1,
                "action": action.get(
                    "recommendation",
                    action.get("action", ""),
                ),
                "priority": action.get(
                    "priority", "medium",
                ),
                "status": "pending",
            }
            steps.append(step)

        return {
            "next_steps": steps,
            "count": len(steps),
            "first_step": (
                steps[0]["action"]
                if steps
                else None
            ),
        }

    def assign_owners(
        self,
        actions: list[dict[str, Any]],
        team: list[str],
    ) -> dict[str, Any]:
        """Sahip atar.

        Args:
            actions: Aksiyon listesi.
            team: Takım üyeleri.

        Returns:
            Atama bilgisi.
        """
        assignments = []
        for i, action in enumerate(actions):
            owner = team[i % len(team)] if (
                team
            ) else "unassigned"
            assignment = {
                "action": action.get(
                    "recommendation",
                    action.get("action", ""),
                ),
                "owner": owner,
                "priority": action.get(
                    "priority", "medium",
                ),
            }
            assignments.append(assignment)
            self._stats[
                "owners_assigned"
            ] += 1

        return {
            "assignments": assignments,
            "count": len(assignments),
            "team_size": len(team),
        }

    def suggest_deadlines(
        self,
        actions: list[dict[str, Any]],
        base_days: int = 7,
    ) -> dict[str, Any]:
        """Son tarih önerir.

        Args:
            actions: Aksiyon listesi.
            base_days: Baz gün sayısı.

        Returns:
            Tarih bilgisi.
        """
        deadlines = []
        priority_multiplier = {
            "critical": 0.5,
            "high": 1.0,
            "medium": 2.0,
            "low": 4.0,
            "info": 8.0,
        }

        for action in actions:
            priority = action.get(
                "priority", "medium",
            )
            mult = priority_multiplier.get(
                priority, 2.0,
            )
            days = int(base_days * mult)

            deadline = {
                "action": action.get(
                    "recommendation",
                    action.get("action", ""),
                ),
                "priority": priority,
                "suggested_days": days,
            }
            deadlines.append(deadline)
            self._stats["deadlines_set"] += 1

        return {
            "deadlines": deadlines,
            "count": len(deadlines),
            "base_days": base_days,
        }

    def get_insights(
        self,
        insight_type: str | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """İçgörüleri getirir.

        Args:
            insight_type: Tip filtresi.
            limit: Maks kayıt.

        Returns:
            İçgörü listesi.
        """
        results = self._insights
        if insight_type:
            results = [
                i for i in results
                if i["type"] == insight_type
            ]
        return list(results[-limit:])

    @property
    def insight_count(self) -> int:
        """İçgörü sayısı."""
        return self._stats[
            "insights_extracted"
        ]

    @property
    def recommendation_count(self) -> int:
        """Öneri sayısı."""
        return self._stats[
            "actions_recommended"
        ]
