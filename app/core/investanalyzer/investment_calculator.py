"""ATLAS Yatırım Hesaplayıcı.

Yatırım modelleme, nakit akışı projeksiyonu,
değerleme yöntemleri, duyarlılık, senaryo karşılaştırma.
"""

import logging
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)


class InvestmentCalculator:
    """Yatırım hesaplayıcı.

    Yatırım modellemesi yapar, nakit akışı
    projekte eder ve değerleme hesaplar.

    Attributes:
        _investments: Yatırım kayıtları.
        _stats: İstatistikler.
    """

    def __init__(self) -> None:
        """Hesaplayıcıyı başlatır."""
        self._investments: dict[
            str, dict
        ] = {}
        self._stats = {
            "models_created": 0,
            "valuations_done": 0,
        }
        logger.info(
            "InvestmentCalculator "
            "baslatildi",
        )

    @property
    def model_count(self) -> int:
        """Model sayısı."""
        return self._stats[
            "models_created"
        ]

    @property
    def valuation_count(self) -> int:
        """Değerleme sayısı."""
        return self._stats[
            "valuations_done"
        ]

    def model_investment(
        self,
        name: str,
        initial_cost: float = 0.0,
        annual_revenue: float = 0.0,
        annual_cost: float = 0.0,
        years: int = 5,
    ) -> dict[str, Any]:
        """Yatırım modeller.

        Args:
            name: Yatırım adı.
            initial_cost: Başlangıç maliyeti.
            annual_revenue: Yıllık gelir.
            annual_cost: Yıllık maliyet.
            years: Yıl sayısı.

        Returns:
            Model bilgisi.
        """
        iid = f"inv_{str(uuid4())[:8]}"
        annual_profit = round(
            annual_revenue - annual_cost,
            2,
        )
        total_profit = round(
            annual_profit * years
            - initial_cost,
            2,
        )

        roi = 0.0
        if initial_cost > 0:
            roi = round(
                total_profit
                / initial_cost
                * 100,
                1,
            )

        self._investments[iid] = {
            "name": name,
            "initial_cost": initial_cost,
            "annual_profit": annual_profit,
            "years": years,
        }
        self._stats[
            "models_created"
        ] += 1

        return {
            "investment_id": iid,
            "name": name,
            "annual_profit": annual_profit,
            "total_profit": total_profit,
            "roi_pct": roi,
            "modeled": True,
        }

    def project_cash_flow(
        self,
        initial_cost: float = 0.0,
        cash_flows: list[float]
        | None = None,
        discount_rate: float = 0.1,
    ) -> dict[str, Any]:
        """Nakit akışı projeksiyonu yapar.

        Args:
            initial_cost: Başlangıç maliyeti.
            cash_flows: Dönemsel nakit akışları.
            discount_rate: İskonto oranı.

        Returns:
            Projeksiyon bilgisi.
        """
        if cash_flows is None:
            cash_flows = []

        npv = -initial_cost
        discounted = []
        for i, cf in enumerate(
            cash_flows, 1,
        ):
            pv = round(
                cf
                / (1 + discount_rate) ** i,
                2,
            )
            discounted.append(pv)
            npv += pv

        npv = round(npv, 2)

        return {
            "initial_cost": initial_cost,
            "npv": npv,
            "total_undiscounted": round(
                sum(cash_flows), 2,
            ),
            "total_discounted": round(
                sum(discounted), 2,
            ),
            "periods": len(cash_flows),
            "profitable": npv > 0,
            "projected": True,
        }

    def valuate_dcf(
        self,
        cash_flows: list[float]
        | None = None,
        discount_rate: float = 0.1,
        terminal_growth: float = 0.02,
    ) -> dict[str, Any]:
        """DCF değerleme yapar.

        Args:
            cash_flows: Nakit akışları.
            discount_rate: İskonto oranı.
            terminal_growth: Terminal büyüme.

        Returns:
            Değerleme bilgisi.
        """
        if cash_flows is None:
            cash_flows = []

        pv_sum = 0.0
        for i, cf in enumerate(
            cash_flows, 1,
        ):
            pv_sum += cf / (
                1 + discount_rate
            ) ** i

        terminal_value = 0.0
        if (
            cash_flows
            and discount_rate
            > terminal_growth
        ):
            last_cf = cash_flows[-1]
            terminal_value = (
                last_cf
                * (1 + terminal_growth)
                / (
                    discount_rate
                    - terminal_growth
                )
            )
            n = len(cash_flows)
            terminal_value /= (
                1 + discount_rate
            ) ** n

        total = round(
            pv_sum + terminal_value, 2,
        )

        self._stats[
            "valuations_done"
        ] += 1

        return {
            "pv_cash_flows": round(
                pv_sum, 2,
            ),
            "terminal_value": round(
                terminal_value, 2,
            ),
            "total_value": total,
            "method": "dcf",
            "valuated": True,
        }

    def sensitivity_analysis(
        self,
        base_npv: float = 0.0,
        variable: str = "discount_rate",
        variations: list[float]
        | None = None,
    ) -> dict[str, Any]:
        """Duyarlılık analizi yapar.

        Args:
            base_npv: Temel NPV.
            variable: Değişken.
            variations: Değişim yüzdeleri.

        Returns:
            Duyarlılık bilgisi.
        """
        if variations is None:
            variations = [
                -20, -10, 0, 10, 20,
            ]

        results = []
        for v in variations:
            adjusted = round(
                base_npv
                * (1 + v / 100),
                2,
            )
            results.append(
                {
                    "variation_pct": v,
                    "npv": adjusted,
                    "profitable": (
                        adjusted > 0
                    ),
                },
            )

        return {
            "base_npv": base_npv,
            "variable": variable,
            "results": results,
            "break_even_variation": next(
                (
                    r["variation_pct"]
                    for r in results
                    if not r["profitable"]
                ),
                None,
            ),
            "analyzed": True,
        }

    def compare_scenarios(
        self,
        scenarios: list[dict[str, Any]]
        | None = None,
    ) -> dict[str, Any]:
        """Senaryo karşılaştırması yapar.

        Args:
            scenarios: Senaryolar
                [{name, npv, roi, risk}].

        Returns:
            Karşılaştırma bilgisi.
        """
        if scenarios is None:
            scenarios = []

        ranked = sorted(
            scenarios,
            key=lambda s: s.get(
                "npv", 0,
            ),
            reverse=True,
        )

        best = (
            ranked[0]["name"]
            if ranked
            else ""
        )

        return {
            "ranked": ranked,
            "best_scenario": best,
            "scenario_count": len(
                scenarios,
            ),
            "compared": True,
        }
