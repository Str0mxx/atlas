"""ATLAS Geri Ödeme Analizcisi.

Geri ödeme süresi, iskontolu geri ödeme,
başa baş analizi, nakit kurtarma, zaman çizelgesi.
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)


class PaybackAnalyzer:
    """Geri ödeme analizcisi.

    Yatırımların geri ödeme süresini
    hesaplar ve başa baş analizi yapar.

    Attributes:
        _analyses: Analiz kayıtları.
        _stats: İstatistikler.
    """

    def __init__(self) -> None:
        """Analizcisi başlatır."""
        self._analyses: list[dict] = []
        self._stats = {
            "paybacks_calculated": 0,
            "breakevens_analyzed": 0,
        }
        logger.info(
            "PaybackAnalyzer baslatildi",
        )

    @property
    def payback_count(self) -> int:
        """Hesaplanan geri ödeme sayısı."""
        return self._stats[
            "paybacks_calculated"
        ]

    @property
    def breakeven_count(self) -> int:
        """Başa baş analizi sayısı."""
        return self._stats[
            "breakevens_analyzed"
        ]

    def calculate_payback(
        self,
        initial_cost: float = 0.0,
        cash_flows: list[float]
        | None = None,
    ) -> dict[str, Any]:
        """Geri ödeme süresi hesaplar.

        Args:
            initial_cost: Başlangıç maliyeti.
            cash_flows: Nakit akışları.

        Returns:
            Geri ödeme bilgisi.
        """
        if cash_flows is None:
            cash_flows = []

        cumulative = 0.0
        payback_period = -1

        for i, cf in enumerate(cash_flows):
            cumulative += cf
            if (
                cumulative >= initial_cost
                and payback_period == -1
            ):
                payback_period = i + 1

        self._stats[
            "paybacks_calculated"
        ] += 1

        return {
            "initial_cost": initial_cost,
            "payback_period": (
                payback_period
            ),
            "total_recovered": round(
                cumulative, 2,
            ),
            "fully_recovered": (
                cumulative >= initial_cost
            ),
            "calculated": True,
        }

    def calculate_discounted_payback(
        self,
        initial_cost: float = 0.0,
        cash_flows: list[float]
        | None = None,
        discount_rate: float = 0.1,
    ) -> dict[str, Any]:
        """İskontolu geri ödeme hesaplar.

        Args:
            initial_cost: Başlangıç maliyeti.
            cash_flows: Nakit akışları.
            discount_rate: İskonto oranı.

        Returns:
            İskontolu geri ödeme bilgisi.
        """
        if cash_flows is None:
            cash_flows = []

        cumulative = 0.0
        payback_period = -1

        for i, cf in enumerate(
            cash_flows, 1,
        ):
            pv = cf / (
                1 + discount_rate
            ) ** i
            cumulative += pv
            if (
                cumulative >= initial_cost
                and payback_period == -1
            ):
                payback_period = i

        self._stats[
            "paybacks_calculated"
        ] += 1

        return {
            "initial_cost": initial_cost,
            "payback_period": (
                payback_period
            ),
            "discount_rate": discount_rate,
            "total_pv": round(
                cumulative, 2,
            ),
            "fully_recovered": (
                cumulative >= initial_cost
            ),
            "calculated": True,
        }

    def analyze_breakeven(
        self,
        fixed_costs: float = 0.0,
        variable_cost_per_unit: float = 0.0,
        price_per_unit: float = 0.0,
    ) -> dict[str, Any]:
        """Başa baş analizi yapar.

        Args:
            fixed_costs: Sabit maliyetler.
            variable_cost_per_unit: Birim
                değişken maliyet.
            price_per_unit: Birim fiyat.

        Returns:
            Başa baş bilgisi.
        """
        margin = (
            price_per_unit
            - variable_cost_per_unit
        )

        if margin <= 0:
            return {
                "breakeven_units": -1,
                "breakeven_revenue": 0.0,
                "feasible": False,
                "analyzed": True,
            }

        be_units = round(
            fixed_costs / margin, 0,
        )
        be_revenue = round(
            be_units * price_per_unit, 2,
        )

        self._stats[
            "breakevens_analyzed"
        ] += 1

        return {
            "breakeven_units": int(
                be_units,
            ),
            "breakeven_revenue": (
                be_revenue
            ),
            "contribution_margin": round(
                margin, 2,
            ),
            "feasible": True,
            "analyzed": True,
        }

    def calculate_cash_recovery(
        self,
        initial_cost: float = 0.0,
        cash_flows: list[float]
        | None = None,
    ) -> dict[str, Any]:
        """Nakit kurtarma hesaplar.

        Args:
            initial_cost: Başlangıç maliyeti.
            cash_flows: Nakit akışları.

        Returns:
            Nakit kurtarma bilgisi.
        """
        if cash_flows is None:
            cash_flows = []

        total = sum(cash_flows)
        recovery_rate = 0.0
        if initial_cost > 0:
            recovery_rate = round(
                total
                / initial_cost
                * 100,
                1,
            )

        cumulative = []
        running = 0.0
        for cf in cash_flows:
            running += cf
            cumulative.append(
                round(running, 2),
            )

        return {
            "initial_cost": initial_cost,
            "total_recovered": round(
                total, 2,
            ),
            "recovery_rate": recovery_rate,
            "cumulative": cumulative,
            "calculated": True,
        }

    def visualize_timeline(
        self,
        initial_cost: float = 0.0,
        cash_flows: list[float]
        | None = None,
    ) -> dict[str, Any]:
        """Zaman çizelgesi görselleştirir.

        Args:
            initial_cost: Başlangıç maliyeti.
            cash_flows: Nakit akışları.

        Returns:
            Görselleştirme bilgisi.
        """
        if cash_flows is None:
            cash_flows = []

        timeline = [
            {
                "period": 0,
                "flow": -initial_cost,
                "cumulative": -initial_cost,
            },
        ]

        cumulative = -initial_cost
        breakeven_period = -1
        for i, cf in enumerate(
            cash_flows, 1,
        ):
            cumulative += cf
            timeline.append(
                {
                    "period": i,
                    "flow": cf,
                    "cumulative": round(
                        cumulative, 2,
                    ),
                },
            )
            if (
                cumulative >= 0
                and breakeven_period == -1
            ):
                breakeven_period = i

        return {
            "timeline": timeline,
            "breakeven_period": (
                breakeven_period
            ),
            "final_cumulative": round(
                cumulative, 2,
            ),
            "visualized": True,
        }
