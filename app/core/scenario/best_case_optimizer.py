"""ATLAS En İyi Durum Optimizasyonu.

Olumlu analiz, fırsat maksimizasyonu,
kaynak tahsisi, zamanlama, başarı faktörleri.
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)


class BestCaseOptimizer:
    """En iyi durum optimizasyonu.

    Senaryoların en iyi olasılıklarını
    optimize eder ve fırsatları maksimize eder.

    Attributes:
        _optimizations: Optimizasyon kayıtları.
        _stats: İstatistikler.
    """

    def __init__(self) -> None:
        """Optimizasyonu başlatır."""
        self._optimizations: dict[
            str, dict
        ] = {}
        self._stats = {
            "analyses_performed": 0,
            "optimizations_made": 0,
        }
        logger.info(
            "BestCaseOptimizer "
            "baslatildi",
        )

    @property
    def analysis_count(self) -> int:
        """Analiz sayısı."""
        return self._stats[
            "analyses_performed"
        ]

    @property
    def optimization_count(self) -> int:
        """Optimizasyon sayısı."""
        return self._stats[
            "optimizations_made"
        ]

    def analyze_upside(
        self,
        scenario_id: str,
        potential_gain: float = 0.0,
        probability: float = 0.3,
        time_to_realize_days: int = 90,
    ) -> dict[str, Any]:
        """Olumlu analiz yapar.

        Args:
            scenario_id: Senaryo kimliği.
            potential_gain: Potansiyel kazanç.
            probability: Olasılık.
            time_to_realize_days: Süre.

        Returns:
            Olumlu analiz bilgisi.
        """
        expected_gain = round(
            potential_gain * probability,
            2,
        )

        if expected_gain >= 100000:
            opportunity = "exceptional"
        elif expected_gain >= 50000:
            opportunity = "significant"
        elif expected_gain >= 10000:
            opportunity = "moderate"
        else:
            opportunity = "marginal"

        self._stats[
            "analyses_performed"
        ] += 1

        return {
            "scenario_id": scenario_id,
            "potential_gain": potential_gain,
            "expected_gain": expected_gain,
            "opportunity": opportunity,
            "days_to_realize": (
                time_to_realize_days
            ),
            "analyzed": True,
        }

    def maximize_opportunity(
        self,
        scenario_id: str,
        opportunities: list[
            dict[str, float]
        ]
        | None = None,
    ) -> dict[str, Any]:
        """Fırsatları maksimize eder.

        Args:
            scenario_id: Senaryo kimliği.
            opportunities: Fırsat listesi
                [{name, value, effort}].

        Returns:
            Maksimizasyon bilgisi.
        """
        if opportunities is None:
            opportunities = []

        ranked = []
        for opp in opportunities:
            value = opp.get("value", 0)
            effort = opp.get("effort", 1)
            if effort <= 0:
                effort = 1
            ratio = round(
                value / effort, 2,
            )
            ranked.append(
                {
                    "name": opp.get(
                        "name", "",
                    ),
                    "value": value,
                    "effort": effort,
                    "ratio": ratio,
                },
            )

        ranked.sort(
            key=lambda x: x["ratio"],
            reverse=True,
        )

        self._stats[
            "optimizations_made"
        ] += 1

        return {
            "scenario_id": scenario_id,
            "ranked": ranked,
            "top_opportunity": (
                ranked[0]["name"]
                if ranked
                else ""
            ),
            "maximized": True,
        }

    def allocate_resources(
        self,
        scenario_id: str,
        total_budget: float = 100.0,
        priorities: list[dict[str, Any]]
        | None = None,
    ) -> dict[str, Any]:
        """Kaynak tahsisi yapar.

        Args:
            scenario_id: Senaryo kimliği.
            total_budget: Toplam bütçe.
            priorities: Öncelikler
                [{name, weight}].

        Returns:
            Tahsis bilgisi.
        """
        if priorities is None:
            priorities = []

        total_weight = sum(
            p.get("weight", 1.0)
            for p in priorities
        )
        if total_weight <= 0:
            total_weight = 1.0

        allocations = []
        for p in priorities:
            w = p.get("weight", 1.0)
            share = round(
                total_budget
                * w
                / total_weight,
                2,
            )
            allocations.append(
                {
                    "name": p.get(
                        "name", "",
                    ),
                    "allocation": share,
                    "percentage": round(
                        w
                        / total_weight
                        * 100,
                        1,
                    ),
                },
            )

        self._stats[
            "optimizations_made"
        ] += 1

        return {
            "scenario_id": scenario_id,
            "total_budget": total_budget,
            "allocations": allocations,
            "allocated": True,
        }

    def optimize_timing(
        self,
        scenario_id: str,
        market_readiness: float = 0.5,
        resource_readiness: float = 0.5,
        competitive_pressure: float = 0.5,
    ) -> dict[str, Any]:
        """Zamanlama optimizasyonu yapar.

        Args:
            scenario_id: Senaryo kimliği.
            market_readiness: Pazar hazırlığı.
            resource_readiness: Kaynak hazırlığı.
            competitive_pressure: Rekabet baskısı.

        Returns:
            Zamanlama bilgisi.
        """
        readiness = round(
            (market_readiness
             + resource_readiness)
            / 2,
            2,
        )

        if (
            readiness >= 0.7
            and competitive_pressure >= 0.7
        ):
            recommendation = "act_now"
        elif readiness >= 0.7:
            recommendation = "prepare_launch"
        elif competitive_pressure >= 0.7:
            recommendation = (
                "accelerate_prep"
            )
        else:
            recommendation = "wait"

        self._stats[
            "analyses_performed"
        ] += 1

        return {
            "scenario_id": scenario_id,
            "readiness": readiness,
            "recommendation": recommendation,
            "optimized": True,
        }

    def identify_success_factors(
        self,
        scenario_id: str,
        factors: list[dict[str, Any]]
        | None = None,
    ) -> dict[str, Any]:
        """Başarı faktörlerini belirler.

        Args:
            scenario_id: Senaryo kimliği.
            factors: Faktörler
                [{name, importance, current}].

        Returns:
            Başarı faktörleri bilgisi.
        """
        if factors is None:
            factors = []

        assessed = []
        for f in factors:
            importance = f.get(
                "importance", 0.5,
            )
            current = f.get(
                "current", 0.5,
            )
            gap = round(
                importance - current, 2,
            )
            assessed.append(
                {
                    "name": f.get(
                        "name", "",
                    ),
                    "importance": importance,
                    "current": current,
                    "gap": gap,
                    "critical": gap > 0.3,
                },
            )

        assessed.sort(
            key=lambda x: x["gap"],
            reverse=True,
        )

        critical_count = sum(
            1
            for a in assessed
            if a["critical"]
        )

        return {
            "scenario_id": scenario_id,
            "factors": assessed,
            "critical_gaps": critical_count,
            "identified": True,
        }
