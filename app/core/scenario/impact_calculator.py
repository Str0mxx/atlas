"""ATLAS Senaryo Etki Hesaplayıcı.

Finansal etki, operasyonel etki,
stratejik etki, zaman etkisi, dalga etkisi.
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)


class ScenarioImpactCalculator:
    """Senaryo etki hesaplayıcısı.

    Senaryoların çeşitli etki boyutlarını
    hesaplar ve değerlendirir.

    Attributes:
        _impacts: Etki kayıtları.
        _stats: İstatistikler.
    """

    def __init__(self) -> None:
        """Hesaplayıcıyı başlatır."""
        self._impacts: dict[
            str, dict
        ] = {}
        self._stats = {
            "calculations_made": 0,
            "ripple_analyses": 0,
        }
        logger.info(
            "ScenarioImpactCalculator "
            "baslatildi",
        )

    @property
    def calculation_count(self) -> int:
        """Hesaplama sayısı."""
        return self._stats[
            "calculations_made"
        ]

    @property
    def ripple_count(self) -> int:
        """Dalga analizi sayısı."""
        return self._stats[
            "ripple_analyses"
        ]

    def calculate_financial(
        self,
        scenario_id: str,
        revenue_change: float = 0.0,
        cost_change: float = 0.0,
        investment_required: float = 0.0,
    ) -> dict[str, Any]:
        """Finansal etki hesaplar.

        Args:
            scenario_id: Senaryo kimliği.
            revenue_change: Gelir değişimi.
            cost_change: Maliyet değişimi.
            investment_required: Yatırım.

        Returns:
            Finansal etki bilgisi.
        """
        net_impact = round(
            revenue_change
            - cost_change
            - investment_required,
            2,
        )

        if investment_required > 0:
            roi = round(
                (revenue_change
                 - cost_change)
                / investment_required
                * 100,
                1,
            )
        else:
            roi = 0.0

        if net_impact > 0:
            direction = "positive"
        elif net_impact < 0:
            direction = "negative"
        else:
            direction = "neutral"

        self._stats[
            "calculations_made"
        ] += 1

        return {
            "scenario_id": scenario_id,
            "net_impact": net_impact,
            "roi": roi,
            "direction": direction,
            "calculated": True,
        }

    def calculate_operational(
        self,
        scenario_id: str,
        efficiency_change: float = 0.0,
        headcount_change: int = 0,
        process_complexity: float = 1.0,
    ) -> dict[str, Any]:
        """Operasyonel etki hesaplar.

        Args:
            scenario_id: Senaryo kimliği.
            efficiency_change: Verimlilik (%).
            headcount_change: Kadro değişimi.
            process_complexity: Süreç karmaşıklığı.

        Returns:
            Operasyonel etki bilgisi.
        """
        score = round(
            efficiency_change
            / max(process_complexity, 0.1),
            2,
        )

        if score >= 20:
            severity = "transformative"
        elif score >= 10:
            severity = "significant"
        elif score >= 0:
            severity = "moderate"
        else:
            severity = "disruptive"

        self._stats[
            "calculations_made"
        ] += 1

        return {
            "scenario_id": scenario_id,
            "score": score,
            "headcount_change": (
                headcount_change
            ),
            "severity": severity,
            "calculated": True,
        }

    def calculate_strategic(
        self,
        scenario_id: str,
        market_position: float = 0.0,
        competitive_advantage: float = 0.0,
        brand_impact: float = 0.0,
        weights: dict[str, float]
        | None = None,
    ) -> dict[str, Any]:
        """Stratejik etki hesaplar.

        Args:
            scenario_id: Senaryo kimliği.
            market_position: Pazar pozisyonu.
            competitive_advantage: Rekabet.
            brand_impact: Marka etkisi.
            weights: Ağırlıklar.

        Returns:
            Stratejik etki bilgisi.
        """
        if weights is None:
            weights = {
                "market": 0.4,
                "competitive": 0.35,
                "brand": 0.25,
            }

        w_m = weights.get("market", 0.4)
        w_c = weights.get(
            "competitive", 0.35,
        )
        w_b = weights.get("brand", 0.25)

        strategic_score = round(
            market_position * w_m
            + competitive_advantage * w_c
            + brand_impact * w_b,
            2,
        )

        self._stats[
            "calculations_made"
        ] += 1

        return {
            "scenario_id": scenario_id,
            "strategic_score": (
                strategic_score
            ),
            "components": {
                "market": market_position,
                "competitive": (
                    competitive_advantage
                ),
                "brand": brand_impact,
            },
            "calculated": True,
        }

    def estimate_timeline(
        self,
        scenario_id: str,
        phases: list[dict[str, Any]]
        | None = None,
    ) -> dict[str, Any]:
        """Zaman etkisi tahmin eder.

        Args:
            scenario_id: Senaryo kimliği.
            phases: Aşamalar
                [{name, duration_days}].

        Returns:
            Zaman etkisi bilgisi.
        """
        if phases is None:
            phases = []

        total_days = sum(
            p.get("duration_days", 0)
            for p in phases
        )

        if total_days <= 30:
            urgency = "immediate"
        elif total_days <= 90:
            urgency = "short_term"
        elif total_days <= 365:
            urgency = "medium_term"
        else:
            urgency = "long_term"

        self._stats[
            "calculations_made"
        ] += 1

        return {
            "scenario_id": scenario_id,
            "total_days": total_days,
            "phase_count": len(phases),
            "urgency": urgency,
            "estimated": True,
        }

    def analyze_ripple(
        self,
        scenario_id: str,
        primary_impact: float = 0.0,
        affected_areas: list[str]
        | None = None,
        decay_factor: float = 0.5,
    ) -> dict[str, Any]:
        """Dalga etkisi analiz eder.

        Args:
            scenario_id: Senaryo kimliği.
            primary_impact: Birincil etki.
            affected_areas: Etkilenen alanlar.
            decay_factor: Azalma faktörü.

        Returns:
            Dalga etkisi bilgisi.
        """
        if affected_areas is None:
            affected_areas = []

        ripples = []
        current = primary_impact
        for area in affected_areas:
            current = round(
                current * decay_factor,
                2,
            )
            ripples.append(
                {
                    "area": area,
                    "impact": current,
                },
            )

        total = round(
            primary_impact
            + sum(
                r["impact"]
                for r in ripples
            ),
            2,
        )

        self._stats[
            "ripple_analyses"
        ] += 1

        return {
            "scenario_id": scenario_id,
            "primary_impact": primary_impact,
            "ripples": ripples,
            "total_impact": total,
            "analyzed": True,
        }
