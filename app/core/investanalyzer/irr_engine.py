"""ATLAS İç Verim Oranı Motoru.

IRR hesaplama, MIRR hesaplama,
çoklu IRR, eşik oranı, sıralama.
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)


class IRREngine:
    """İç verim oranı motoru.

    IRR ve MIRR hesaplar, eşik oranlarıyla
    karşılaştırır ve yatırımları sıralar.

    Attributes:
        _calculations: Hesaplama kayıtları.
        _stats: İstatistikler.
    """

    def __init__(self) -> None:
        """Motoru başlatır."""
        self._calculations: list[
            dict
        ] = []
        self._stats = {
            "irr_calculated": 0,
            "rankings_done": 0,
        }
        logger.info(
            "IRREngine baslatildi",
        )

    @property
    def calculation_count(self) -> int:
        """Hesaplama sayısı."""
        return self._stats[
            "irr_calculated"
        ]

    @property
    def ranking_count(self) -> int:
        """Sıralama sayısı."""
        return self._stats[
            "rankings_done"
        ]

    def calculate_irr(
        self,
        initial_cost: float = 0.0,
        cash_flows: list[float]
        | None = None,
        max_iterations: int = 100,
    ) -> dict[str, Any]:
        """IRR hesaplar (Newton-Raphson).

        Args:
            initial_cost: Başlangıç maliyeti.
            cash_flows: Nakit akışları.
            max_iterations: Maks iterasyon.

        Returns:
            IRR bilgisi.
        """
        if cash_flows is None:
            cash_flows = []

        flows = [-initial_cost] + cash_flows

        if not cash_flows or all(
            cf <= 0 for cf in cash_flows
        ):
            return {
                "irr": 0.0,
                "converged": False,
                "calculated": True,
            }

        rate = 0.1
        for _ in range(max_iterations):
            npv = sum(
                f / (1 + rate) ** i
                for i, f in enumerate(
                    flows,
                )
            )
            dnpv = sum(
                -i
                * f
                / (1 + rate) ** (i + 1)
                for i, f in enumerate(
                    flows,
                )
            )
            if abs(dnpv) < 1e-10:
                break
            rate -= npv / dnpv
            if abs(npv) < 0.01:
                break

        irr = round(rate * 100, 2)
        self._stats[
            "irr_calculated"
        ] += 1

        return {
            "irr": irr,
            "irr_decimal": round(rate, 4),
            "converged": abs(npv) < 1.0,
            "calculated": True,
        }

    def calculate_mirr(
        self,
        initial_cost: float = 0.0,
        cash_flows: list[float]
        | None = None,
        finance_rate: float = 0.1,
        reinvest_rate: float = 0.1,
    ) -> dict[str, Any]:
        """MIRR hesaplar.

        Args:
            initial_cost: Başlangıç maliyeti.
            cash_flows: Nakit akışları.
            finance_rate: Finansman oranı.
            reinvest_rate: Yeniden yatırım.

        Returns:
            MIRR bilgisi.
        """
        if cash_flows is None:
            cash_flows = []

        n = len(cash_flows)
        if n == 0 or initial_cost <= 0:
            return {
                "mirr": 0.0,
                "calculated": True,
            }

        fv_positive = 0.0
        pv_negative = initial_cost

        for i, cf in enumerate(cash_flows):
            if cf >= 0:
                power = n - i - 1
                fv_positive += cf * (
                    1 + reinvest_rate
                ) ** power
            else:
                pv_negative += abs(cf) / (
                    1 + finance_rate
                ) ** (i + 1)

        if pv_negative <= 0:
            pv_negative = 0.01

        mirr = round(
            (
                (fv_positive / pv_negative)
                ** (1 / n)
                - 1
            )
            * 100,
            2,
        )

        self._stats[
            "irr_calculated"
        ] += 1

        return {
            "mirr": mirr,
            "fv_positive": round(
                fv_positive, 2,
            ),
            "pv_negative": round(
                pv_negative, 2,
            ),
            "calculated": True,
        }

    def handle_multiple_irr(
        self,
        cash_flows: list[float]
        | None = None,
    ) -> dict[str, Any]:
        """Çoklu IRR kontrolü yapar.

        Args:
            cash_flows: Nakit akışları
                (başlangıç dahil).

        Returns:
            Çoklu IRR bilgisi.
        """
        if cash_flows is None:
            cash_flows = []

        sign_changes = 0
        for i in range(
            1, len(cash_flows),
        ):
            if (
                cash_flows[i]
                * cash_flows[i - 1]
                < 0
            ):
                sign_changes += 1

        multiple = sign_changes > 1

        return {
            "sign_changes": sign_changes,
            "multiple_irr_possible": (
                multiple
            ),
            "recommendation": (
                "use_mirr"
                if multiple
                else "use_irr"
            ),
            "analyzed": True,
        }

    def compare_hurdle(
        self,
        irr: float = 0.0,
        hurdle_rate: float = 10.0,
    ) -> dict[str, Any]:
        """Eşik oranıyla karşılaştırır.

        Args:
            irr: İç verim oranı (%).
            hurdle_rate: Eşik oranı (%).

        Returns:
            Karşılaştırma bilgisi.
        """
        spread = round(
            irr - hurdle_rate, 2,
        )
        acceptable = irr >= hurdle_rate

        if spread >= 10:
            verdict = "excellent"
        elif spread >= 5:
            verdict = "good"
        elif spread >= 0:
            verdict = "marginal"
        else:
            verdict = "reject"

        return {
            "irr": irr,
            "hurdle_rate": hurdle_rate,
            "spread": spread,
            "acceptable": acceptable,
            "verdict": verdict,
            "compared": True,
        }

    def rank_investments(
        self,
        investments: list[dict[str, Any]]
        | None = None,
    ) -> dict[str, Any]:
        """Yatırımları sıralar.

        Args:
            investments: Yatırımlar
                [{name, irr}].

        Returns:
            Sıralama bilgisi.
        """
        if investments is None:
            investments = []

        ranked = sorted(
            investments,
            key=lambda x: x.get(
                "irr", 0,
            ),
            reverse=True,
        )

        for i, inv in enumerate(
            ranked, 1,
        ):
            inv["rank"] = i

        self._stats[
            "rankings_done"
        ] += 1

        return {
            "ranked": ranked,
            "best": (
                ranked[0]["name"]
                if ranked
                else ""
            ),
            "count": len(ranked),
            "ranked_done": True,
        }
