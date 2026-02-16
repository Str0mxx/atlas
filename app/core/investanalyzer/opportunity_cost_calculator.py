"""ATLAS Fırsat Maliyeti Hesaplayıcı.

Fırsat maliyeti, alternatif analizi,
kaynak tahsisi, takas analizi, en iyi kullanım.
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)


class OpportunityCostCalculator:
    """Fırsat maliyeti hesaplayıcı.

    Yatırımların fırsat maliyetini hesaplar,
    alternatifleri analiz eder.

    Attributes:
        _calculations: Hesaplama kayıtları.
        _stats: İstatistikler.
    """

    def __init__(self) -> None:
        """Hesaplayıcıyı başlatır."""
        self._calculations: list[
            dict
        ] = []
        self._stats = {
            "costs_calculated": 0,
            "analyses_done": 0,
        }
        logger.info(
            "OpportunityCostCalculator "
            "baslatildi",
        )

    @property
    def calculation_count(self) -> int:
        """Hesaplama sayısı."""
        return self._stats[
            "costs_calculated"
        ]

    @property
    def analysis_count(self) -> int:
        """Analiz sayısı."""
        return self._stats[
            "analyses_done"
        ]

    def calculate_opportunity_cost(
        self,
        chosen_return: float = 0.0,
        best_alternative_return: float = 0.0,
        investment_amount: float = 0.0,
    ) -> dict[str, Any]:
        """Fırsat maliyeti hesaplar.

        Args:
            chosen_return: Seçilen getiri (%).
            best_alternative_return: En iyi
                alternatif getiri (%).
            investment_amount: Yatırım tutarı.

        Returns:
            Fırsat maliyeti bilgisi.
        """
        cost_pct = round(
            best_alternative_return
            - chosen_return,
            2,
        )
        cost_amount = round(
            investment_amount
            * cost_pct
            / 100,
            2,
        )

        if cost_pct <= 0:
            verdict = "optimal_choice"
        elif cost_pct <= 5:
            verdict = "acceptable"
        else:
            verdict = "reconsider"

        self._stats[
            "costs_calculated"
        ] += 1

        return {
            "chosen_return": chosen_return,
            "best_alternative": (
                best_alternative_return
            ),
            "opportunity_cost_pct": cost_pct,
            "opportunity_cost_amount": (
                cost_amount
            ),
            "verdict": verdict,
            "calculated": True,
        }

    def analyze_alternatives(
        self,
        alternatives: list[
            dict[str, Any]
        ]
        | None = None,
    ) -> dict[str, Any]:
        """Alternatif analizi yapar.

        Args:
            alternatives: Alternatifler
                [{name, return_pct, risk}].

        Returns:
            Alternatif bilgisi.
        """
        if alternatives is None:
            alternatives = []

        ranked = sorted(
            alternatives,
            key=lambda a: a.get(
                "return_pct", 0,
            ),
            reverse=True,
        )

        best = (
            ranked[0]["name"]
            if ranked
            else ""
        )

        self._stats[
            "analyses_done"
        ] += 1

        return {
            "alternatives": ranked,
            "best_alternative": best,
            "count": len(alternatives),
            "analyzed": True,
        }

    def allocate_resources(
        self,
        total_budget: float = 0.0,
        options: list[dict[str, Any]]
        | None = None,
    ) -> dict[str, Any]:
        """Kaynak tahsisi yapar.

        Args:
            total_budget: Toplam bütçe.
            options: Seçenekler
                [{name, min_invest, return_pct}].

        Returns:
            Tahsis bilgisi.
        """
        if options is None:
            options = []

        sorted_opts = sorted(
            options,
            key=lambda o: o.get(
                "return_pct", 0,
            ),
            reverse=True,
        )

        allocations = []
        remaining = total_budget
        for opt in sorted_opts:
            min_inv = opt.get(
                "min_invest", 0,
            )
            if remaining >= min_inv:
                alloc = min(
                    remaining, min_inv * 2,
                )
                allocations.append(
                    {
                        "name": opt.get(
                            "name", "",
                        ),
                        "allocation": round(
                            alloc, 2,
                        ),
                    },
                )
                remaining -= alloc

        return {
            "total_budget": total_budget,
            "allocated": round(
                total_budget - remaining,
                2,
            ),
            "remaining": round(
                remaining, 2,
            ),
            "allocations": allocations,
            "allocated_done": True,
        }

    def analyze_tradeoff(
        self,
        option_a: dict[str, Any]
        | None = None,
        option_b: dict[str, Any]
        | None = None,
    ) -> dict[str, Any]:
        """Takas analizi yapar.

        Args:
            option_a: Seçenek A
                {name, return_pct, risk}.
            option_b: Seçenek B.

        Returns:
            Takas bilgisi.
        """
        if option_a is None:
            option_a = {}
        if option_b is None:
            option_b = {}

        ret_a = option_a.get(
            "return_pct", 0,
        )
        ret_b = option_b.get(
            "return_pct", 0,
        )
        risk_a = option_a.get("risk", 0.5)
        risk_b = option_b.get("risk", 0.5)

        return_diff = round(
            ret_a - ret_b, 2,
        )
        risk_diff = round(
            risk_a - risk_b, 3,
        )

        if return_diff > 0 and risk_diff < 0:
            winner = option_a.get(
                "name", "A",
            )
            dominant = True
        elif (
            return_diff < 0
            and risk_diff > 0
        ):
            winner = option_b.get(
                "name", "B",
            )
            dominant = True
        else:
            winner = (
                option_a.get("name", "A")
                if return_diff > 0
                else option_b.get(
                    "name", "B",
                )
            )
            dominant = False

        self._stats[
            "analyses_done"
        ] += 1

        return {
            "return_difference": return_diff,
            "risk_difference": risk_diff,
            "winner": winner,
            "dominant": dominant,
            "analyzed": True,
        }

    def determine_best_use(
        self,
        resource_amount: float = 0.0,
        uses: list[dict[str, Any]]
        | None = None,
    ) -> dict[str, Any]:
        """En iyi kullanımı belirler.

        Args:
            resource_amount: Kaynak miktarı.
            uses: Kullanımlar
                [{name, return_per_unit}].

        Returns:
            En iyi kullanım bilgisi.
        """
        if uses is None:
            uses = []

        ranked = sorted(
            uses,
            key=lambda u: u.get(
                "return_per_unit", 0,
            ),
            reverse=True,
        )

        best = (
            ranked[0]["name"]
            if ranked
            else ""
        )
        best_return = (
            round(
                resource_amount
                * ranked[0].get(
                    "return_per_unit", 0,
                ),
                2,
            )
            if ranked
            else 0.0
        )

        return {
            "resource_amount": (
                resource_amount
            ),
            "best_use": best,
            "expected_return": best_return,
            "alternatives": len(ranked),
            "determined": True,
        }
