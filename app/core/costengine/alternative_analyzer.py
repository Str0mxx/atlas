"""ATLAS Alternatif Analizcisi modulu.

Alternatif karsilastirma, maliyet-fayda analizi,
ROI hesaplama, trade-off, oneri.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class AlternativeAnalyzer:
    """Alternatif analizcisi.

    Karar alternatifleri analiz eder.

    Attributes:
        _analyses: Analiz kayitlari.
    """

    def __init__(self) -> None:
        """Alternatif analizcisini baslatir."""
        self._analyses: list[
            dict[str, Any]
        ] = []
        self._stats = {
            "analyzed": 0,
        }

        logger.info(
            "AlternativeAnalyzer baslatildi",
        )

    def compare_alternatives(
        self,
        decision_id: str,
        alternatives: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Alternatifleri karsilastirir.

        Args:
            decision_id: Karar ID.
            alternatives: Alternatifler
                [{name, cost, benefit, risk}].

        Returns:
            Karsilastirma sonucu.
        """
        if not alternatives:
            return {"error": "no_alternatives"}

        ranked = sorted(
            alternatives,
            key=lambda a: (
                a.get("benefit", 0)
                - a.get("cost", 0)
            ),
            reverse=True,
        )

        for i, alt in enumerate(ranked):
            alt["rank"] = i + 1
            alt["net_value"] = (
                alt.get("benefit", 0)
                - alt.get("cost", 0)
            )

        best = ranked[0]

        result = {
            "decision_id": decision_id,
            "alternatives": ranked,
            "best": best["name"],
            "best_net_value": best["net_value"],
            "count": len(alternatives),
            "timestamp": time.time(),
        }

        self._analyses.append(result)
        self._stats["analyzed"] += 1

        return result

    def cost_benefit_analysis(
        self,
        name: str,
        costs: list[float],
        benefits: list[float],
        discount_rate: float = 0.0,
    ) -> dict[str, Any]:
        """Maliyet-fayda analizi yapar.

        Args:
            name: Analiz adi.
            costs: Maliyet listesi.
            benefits: Fayda listesi.
            discount_rate: Iskonto orani.

        Returns:
            Analiz sonucu.
        """
        total_cost = sum(costs)
        total_benefit = sum(benefits)

        # Iskonto uygula
        if discount_rate > 0:
            discounted_costs = sum(
                c / (1 + discount_rate) ** i
                for i, c in enumerate(costs)
            )
            discounted_benefits = sum(
                b / (1 + discount_rate) ** i
                for i, b in enumerate(benefits)
            )
        else:
            discounted_costs = total_cost
            discounted_benefits = total_benefit

        net = discounted_benefits - discounted_costs
        ratio = (
            discounted_benefits / discounted_costs
            if discounted_costs > 0
            else float("inf")
        )

        result = {
            "name": name,
            "total_cost": round(total_cost, 4),
            "total_benefit": round(
                total_benefit, 4,
            ),
            "net_benefit": round(net, 4),
            "bcr": round(ratio, 4),
            "viable": net > 0,
            "timestamp": time.time(),
        }

        self._analyses.append(result)
        self._stats["analyzed"] += 1

        return result

    def calculate_roi(
        self,
        name: str,
        investment: float,
        returns: float,
        period: str = "",
    ) -> dict[str, Any]:
        """ROI hesaplar.

        Args:
            name: Yatirim adi.
            investment: Yatirim miktari.
            returns: Getiri.
            period: Donem.

        Returns:
            ROI bilgisi.
        """
        if investment == 0:
            roi_pct = (
                float("inf")
                if returns > 0
                else 0.0
            )
        else:
            roi_pct = (
                (returns - investment)
                / investment * 100
            )

        profit = returns - investment

        result = {
            "name": name,
            "investment": investment,
            "returns": returns,
            "profit": round(profit, 4),
            "roi_pct": round(roi_pct, 2),
            "profitable": profit > 0,
            "period": period,
            "timestamp": time.time(),
        }

        self._analyses.append(result)
        self._stats["analyzed"] += 1

        return result

    def trade_off_analysis(
        self,
        decision_id: str,
        option_a: dict[str, Any],
        option_b: dict[str, Any],
        weights: dict[str, float] | None = None,
    ) -> dict[str, Any]:
        """Trade-off analizi yapar.

        Args:
            decision_id: Karar ID.
            option_a: Secenek A {criteria: score}.
            option_b: Secenek B {criteria: score}.
            weights: Kriter agirliklari.

        Returns:
            Trade-off sonucu.
        """
        w = weights or {}
        all_criteria = set(
            list(option_a.keys())
            + list(option_b.keys())
        )
        # name key'ini cikar
        all_criteria.discard("name")

        score_a = 0.0
        score_b = 0.0
        details = {}

        for c in all_criteria:
            val_a = option_a.get(c, 0.0)
            val_b = option_b.get(c, 0.0)
            weight = w.get(c, 1.0)

            score_a += val_a * weight
            score_b += val_b * weight

            details[c] = {
                "a": val_a,
                "b": val_b,
                "weight": weight,
                "winner": (
                    "a" if val_a > val_b
                    else "b" if val_b > val_a
                    else "tie"
                ),
            }

        winner = (
            "a" if score_a > score_b
            else "b" if score_b > score_a
            else "tie"
        )

        result = {
            "decision_id": decision_id,
            "score_a": round(score_a, 4),
            "score_b": round(score_b, 4),
            "winner": winner,
            "criteria": details,
            "timestamp": time.time(),
        }

        self._analyses.append(result)
        self._stats["analyzed"] += 1

        return result

    def recommend(
        self,
        decision_id: str,
        alternatives: list[dict[str, Any]],
        max_cost: float | None = None,
        min_benefit: float | None = None,
    ) -> dict[str, Any]:
        """Oneri verir.

        Args:
            decision_id: Karar ID.
            alternatives: Alternatifler.
            max_cost: Maks maliyet.
            min_benefit: Min fayda.

        Returns:
            Oneri.
        """
        filtered = alternatives

        if max_cost is not None:
            filtered = [
                a for a in filtered
                if a.get("cost", 0) <= max_cost
            ]

        if min_benefit is not None:
            filtered = [
                a for a in filtered
                if a.get("benefit", 0) >= min_benefit
            ]

        if not filtered:
            return {
                "decision_id": decision_id,
                "recommendation": None,
                "reason": "no_viable_options",
            }

        best = max(
            filtered,
            key=lambda a: (
                a.get("benefit", 0)
                - a.get("cost", 0)
            ),
        )

        return {
            "decision_id": decision_id,
            "recommendation": best.get("name"),
            "cost": best.get("cost", 0),
            "benefit": best.get("benefit", 0),
            "net_value": (
                best.get("benefit", 0)
                - best.get("cost", 0)
            ),
            "alternatives_considered": len(
                alternatives,
            ),
            "viable_options": len(filtered),
        }

    def get_analyses(
        self,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """Analizleri getirir.

        Args:
            limit: Limit.

        Returns:
            Analiz listesi.
        """
        return list(self._analyses[-limit:])

    @property
    def analysis_count(self) -> int:
        """Analiz sayisi."""
        return self._stats["analyzed"]
