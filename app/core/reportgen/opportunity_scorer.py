"""ATLAS Fırsat Puanlayıcı modülü.

Fırsat sıralama, ROI tahmini,
risk değerlendirme, fizibilite puanlama,
öncelik sıralama.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class OpportunityScorer:
    """Fırsat puanlayıcı.

    Fırsatları değerlendirir ve sıralar.

    Attributes:
        _opportunities: Fırsat geçmişi.
    """

    def __init__(
        self,
        weights: dict[str, float] | None = None,
    ) -> None:
        """Puanlayıcıyı başlatır.

        Args:
            weights: Kriter ağırlıkları.
        """
        self._opportunities: list[
            dict[str, Any]
        ] = []
        self._weights = weights or {
            "roi": 0.3,
            "risk": 0.2,
            "feasibility": 0.25,
            "impact": 0.25,
        }
        self._counter = 0
        self._stats = {
            "opportunities_scored": 0,
            "rankings_generated": 0,
        }

        logger.info(
            "OpportunityScorer baslatildi",
        )

    def score_opportunity(
        self,
        name: str,
        roi_estimate: float,
        risk_level: float,
        feasibility: float,
        impact: float,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Fırsatı puanlar.

        Args:
            name: Fırsat adı.
            roi_estimate: ROI tahmini (0-10).
            risk_level: Risk (0-10, düşük iyi).
            feasibility: Fizibilite (0-10).
            impact: Etki (0-10).
            metadata: Ek bilgiler.

        Returns:
            Puanlama bilgisi.
        """
        self._counter += 1
        oid = f"opp_{self._counter}"

        # Risk tersi (düşük risk = yüksek puan)
        risk_score = 10.0 - risk_level

        weighted = (
            roi_estimate
            * self._weights.get("roi", 0.3)
            + risk_score
            * self._weights.get("risk", 0.2)
            + feasibility
            * self._weights.get(
                "feasibility", 0.25,
            )
            + impact
            * self._weights.get(
                "impact", 0.25,
            )
        )
        final_score = round(weighted, 2)

        opportunity = {
            "opportunity_id": oid,
            "name": name,
            "scores": {
                "roi": roi_estimate,
                "risk": risk_level,
                "feasibility": feasibility,
                "impact": impact,
            },
            "final_score": final_score,
            "metadata": metadata or {},
            "scored_at": time.time(),
        }
        self._opportunities.append(
            opportunity,
        )
        self._stats[
            "opportunities_scored"
        ] += 1

        return {
            "opportunity_id": oid,
            "name": name,
            "final_score": final_score,
            "roi": roi_estimate,
            "risk": risk_level,
            "feasibility": feasibility,
            "impact": impact,
            "scored": True,
        }

    def estimate_roi(
        self,
        investment: float,
        expected_return: float,
        timeframe_months: int = 12,
    ) -> dict[str, Any]:
        """ROI tahmin eder.

        Args:
            investment: Yatırım.
            expected_return: Beklenen getiri.
            timeframe_months: Süre (ay).

        Returns:
            ROI bilgisi.
        """
        if investment <= 0:
            return {
                "error": "invalid_investment",
            }

        roi_pct = round(
            (
                (expected_return - investment)
                / investment
            ) * 100,
            2,
        )
        monthly_return = round(
            (expected_return - investment)
            / timeframe_months,
            2,
        )
        payback_months = (
            round(
                investment
                / (
                    expected_return
                    / timeframe_months
                ),
                1,
            )
            if expected_return > 0
            else float("inf")
        )

        return {
            "roi_percentage": roi_pct,
            "monthly_return": monthly_return,
            "payback_months": payback_months,
            "investment": investment,
            "expected_return": expected_return,
            "timeframe_months": timeframe_months,
        }

    def assess_risk(
        self,
        factors: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Risk değerlendirir.

        Args:
            factors: Risk faktörleri.

        Returns:
            Değerlendirme bilgisi.
        """
        if not factors:
            return {
                "overall_risk": 0.0,
                "factors": [],
                "level": "low",
            }

        total = sum(
            f.get("severity", 5)
            * f.get("probability", 0.5)
            for f in factors
        )
        avg = total / len(factors)

        level = "low"
        if avg > 6:
            level = "critical"
        elif avg > 4:
            level = "high"
        elif avg > 2:
            level = "medium"

        return {
            "overall_risk": round(avg, 2),
            "risk_level": level,
            "factor_count": len(factors),
            "factors": factors,
        }

    def score_feasibility(
        self,
        resources_available: float,
        technical_complexity: float,
        team_capability: float,
        time_constraint: float,
    ) -> dict[str, Any]:
        """Fizibilite puanlar.

        Args:
            resources_available: Kaynak (0-10).
            technical_complexity: Karmaşıklık
                (0-10, düşük iyi).
            team_capability: Yetenek (0-10).
            time_constraint: Zaman kısıtı
                (0-10, düşük iyi).

        Returns:
            Fizibilite bilgisi.
        """
        score = (
            resources_available * 0.3
            + (10 - technical_complexity) * 0.25
            + team_capability * 0.25
            + (10 - time_constraint) * 0.2
        )

        level = "low"
        if score >= 7:
            level = "high"
        elif score >= 4:
            level = "medium"

        return {
            "feasibility_score": round(
                score, 2,
            ),
            "level": level,
            "resources": resources_available,
            "complexity": technical_complexity,
            "capability": team_capability,
            "time_pressure": time_constraint,
        }

    def rank_opportunities(
        self,
    ) -> dict[str, Any]:
        """Fırsatları sıralar.

        Returns:
            Sıralama bilgisi.
        """
        ranked = sorted(
            self._opportunities,
            key=lambda x: x["final_score"],
            reverse=True,
        )
        for i, opp in enumerate(ranked):
            opp["rank"] = i + 1

        self._stats["rankings_generated"] += 1

        return {
            "ranked": [
                {
                    "rank": o["rank"],
                    "name": o["name"],
                    "score": o["final_score"],
                    "opportunity_id": o[
                        "opportunity_id"
                    ],
                }
                for o in ranked
            ],
            "count": len(ranked),
            "top": (
                ranked[0]["name"]
                if ranked
                else None
            ),
        }

    def get_opportunities(
        self,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """Fırsatları getirir.

        Args:
            limit: Maks kayıt.

        Returns:
            Fırsat listesi.
        """
        return list(
            self._opportunities[-limit:],
        )

    @property
    def scored_count(self) -> int:
        """Puanlanan fırsat sayısı."""
        return self._stats[
            "opportunities_scored"
        ]

    @property
    def ranking_count(self) -> int:
        """Sıralama sayısı."""
        return self._stats[
            "rankings_generated"
        ]
