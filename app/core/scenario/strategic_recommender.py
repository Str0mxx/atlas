"""ATLAS Stratejik Önerici.

Strateji önerileri, risk-getiri dengesi,
öncelik sıralama, eylem planlama, olasılık planı.
"""

import logging
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)


class StrategicRecommender:
    """Stratejik önerici.

    Senaryo analizlerine dayalı stratejik
    öneriler üretir ve eylem planları oluşturur.

    Attributes:
        _recommendations: Öneri kayıtları.
        _stats: İstatistikler.
    """

    def __init__(self) -> None:
        """Önericisi başlatır."""
        self._recommendations: dict[
            str, dict
        ] = {}
        self._stats = {
            "recommendations_made": 0,
            "plans_created": 0,
        }
        logger.info(
            "StrategicRecommender "
            "baslatildi",
        )

    @property
    def recommendation_count(self) -> int:
        """Öneri sayısı."""
        return self._stats[
            "recommendations_made"
        ]

    @property
    def plan_count(self) -> int:
        """Plan sayısı."""
        return self._stats[
            "plans_created"
        ]

    def suggest_strategy(
        self,
        scenario_id: str,
        risk_level: str = "medium",
        opportunity_level: str = "medium",
        time_horizon: str = "medium_term",
    ) -> dict[str, Any]:
        """Strateji önerir.

        Args:
            scenario_id: Senaryo kimliği.
            risk_level: Risk seviyesi.
            opportunity_level: Fırsat seviyesi.
            time_horizon: Zaman ufku.

        Returns:
            Strateji önerisi bilgisi.
        """
        if (
            risk_level == "low"
            and opportunity_level == "high"
        ):
            strategy = "aggressive"
        elif (
            risk_level == "high"
            and opportunity_level == "low"
        ):
            strategy = "defensive"
        elif (
            risk_level == "high"
            and opportunity_level == "high"
        ):
            strategy = "calculated_risk"
        else:
            strategy = "balanced"

        rid = f"rec_{str(uuid4())[:6]}"
        self._recommendations[rid] = {
            "strategy": strategy,
            "scenario_id": scenario_id,
        }
        self._stats[
            "recommendations_made"
        ] += 1

        return {
            "recommendation_id": rid,
            "scenario_id": scenario_id,
            "strategy": strategy,
            "time_horizon": time_horizon,
            "suggested": True,
        }

    def balance_risk_reward(
        self,
        scenario_id: str,
        potential_reward: float = 0.0,
        potential_risk: float = 0.0,
        risk_tolerance: float = 0.5,
    ) -> dict[str, Any]:
        """Risk-getiri dengesi kurar.

        Args:
            scenario_id: Senaryo kimliği.
            potential_reward: Potansiyel getiri.
            potential_risk: Potansiyel risk.
            risk_tolerance: Risk toleransı.

        Returns:
            Denge bilgisi.
        """
        if potential_risk <= 0:
            ratio = 999.0
        else:
            ratio = round(
                potential_reward
                / potential_risk,
                2,
            )

        if ratio >= 3.0:
            verdict = "strongly_favorable"
        elif ratio >= 1.5:
            verdict = "favorable"
        elif ratio >= 1.0:
            verdict = "neutral"
        elif ratio >= 0.5:
            verdict = "unfavorable"
        else:
            verdict = "strongly_unfavorable"

        proceed = (
            ratio >= 1.0 / max(
                risk_tolerance, 0.01,
            )
        )

        self._stats[
            "recommendations_made"
        ] += 1

        return {
            "scenario_id": scenario_id,
            "risk_reward_ratio": ratio,
            "verdict": verdict,
            "proceed": proceed,
            "balanced": True,
        }

    def rank_priorities(
        self,
        scenario_id: str,
        items: list[dict[str, Any]]
        | None = None,
    ) -> dict[str, Any]:
        """Öncelikleri sıralar.

        Args:
            scenario_id: Senaryo kimliği.
            items: Öncelik öğeleri
                [{name, impact, urgency, effort}].

        Returns:
            Sıralama bilgisi.
        """
        if items is None:
            items = []

        scored = []
        for item in items:
            impact = item.get(
                "impact", 0.5,
            )
            urgency = item.get(
                "urgency", 0.5,
            )
            effort = item.get(
                "effort", 0.5,
            )

            score = round(
                (impact * 0.4
                 + urgency * 0.4)
                / max(effort, 0.1)
                * 0.2,
                3,
            )
            scored.append(
                {
                    "name": item.get(
                        "name", "",
                    ),
                    "score": score,
                    "impact": impact,
                    "urgency": urgency,
                },
            )

        scored.sort(
            key=lambda x: x["score"],
            reverse=True,
        )

        return {
            "scenario_id": scenario_id,
            "ranked": scored,
            "top_priority": (
                scored[0]["name"]
                if scored
                else ""
            ),
            "ranked_count": len(scored),
        }

    def create_action_plan(
        self,
        scenario_id: str,
        strategy: str = "balanced",
        actions: list[str]
        | None = None,
        timeline_days: int = 90,
    ) -> dict[str, Any]:
        """Eylem planı oluşturur.

        Args:
            scenario_id: Senaryo kimliği.
            strategy: Strateji tipi.
            actions: Eylemler.
            timeline_days: Zaman çizelgesi.

        Returns:
            Eylem planı bilgisi.
        """
        if actions is None:
            actions = []

        if not actions:
            actions = self._default_actions(
                strategy,
            )

        phase_count = min(
            len(actions), 4,
        )
        days_per_phase = (
            timeline_days // max(
                phase_count, 1,
            )
        )

        phases = []
        for i, action in enumerate(
            actions[:phase_count],
        ):
            phases.append(
                {
                    "phase": i + 1,
                    "action": action,
                    "duration_days": (
                        days_per_phase
                    ),
                },
            )

        self._stats[
            "plans_created"
        ] += 1

        return {
            "scenario_id": scenario_id,
            "strategy": strategy,
            "phases": phases,
            "total_days": timeline_days,
            "created": True,
        }

    def plan_contingency(
        self,
        scenario_id: str,
        primary_plan: str = "",
        trigger_conditions: list[str]
        | None = None,
        fallback_actions: list[str]
        | None = None,
    ) -> dict[str, Any]:
        """Olasılık planı oluşturur.

        Args:
            scenario_id: Senaryo kimliği.
            primary_plan: Birincil plan.
            trigger_conditions: Tetik koşulları.
            fallback_actions: Yedek eylemler.

        Returns:
            Olasılık planı bilgisi.
        """
        if trigger_conditions is None:
            trigger_conditions = []
        if fallback_actions is None:
            fallback_actions = []

        contingency_count = min(
            len(trigger_conditions),
            len(fallback_actions),
        )

        contingencies = []
        for i in range(contingency_count):
            contingencies.append(
                {
                    "trigger": (
                        trigger_conditions[i]
                    ),
                    "action": (
                        fallback_actions[i]
                    ),
                    "plan_label": (
                        chr(66 + i)
                    ),
                },
            )

        self._stats[
            "plans_created"
        ] += 1

        return {
            "scenario_id": scenario_id,
            "primary_plan": primary_plan,
            "contingencies": contingencies,
            "contingency_count": (
                contingency_count
            ),
            "planned": True,
        }

    def _default_actions(
        self, strategy: str,
    ) -> list[str]:
        """Varsayılan eylemler.

        Args:
            strategy: Strateji tipi.

        Returns:
            Eylem listesi.
        """
        defaults = {
            "aggressive": [
                "rapid_expansion",
                "market_capture",
                "scale_operations",
            ],
            "defensive": [
                "fortify_position",
                "reduce_costs",
                "secure_partnerships",
            ],
            "balanced": [
                "assess_market",
                "pilot_program",
                "measured_growth",
            ],
        }
        return defaults.get(
            strategy,
            ["evaluate", "plan", "execute"],
        )
