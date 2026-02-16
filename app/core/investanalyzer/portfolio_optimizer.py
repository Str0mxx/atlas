"""ATLAS Portföy Optimizasyonu.

Portföy oluşturma, çeşitlendirme,
yeniden dengeleme, risk yönetimi, performans.
"""

import logging
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)


class InvestmentPortfolioOptimizer:
    """Yatırım portföy optimizasyonu.

    Portföy oluşturur, çeşitlendirir,
    dengeler ve performansı izler.

    Attributes:
        _portfolios: Portföy kayıtları.
        _stats: İstatistikler.
    """

    def __init__(self) -> None:
        """Optimizasyonu başlatır."""
        self._portfolios: dict[
            str, dict
        ] = {}
        self._stats = {
            "portfolios_created": 0,
            "rebalances_done": 0,
        }
        logger.info(
            "InvestmentPortfolioOptimizer "
            "baslatildi",
        )

    @property
    def portfolio_count(self) -> int:
        """Portföy sayısı."""
        return self._stats[
            "portfolios_created"
        ]

    @property
    def rebalance_count(self) -> int:
        """Yeniden dengeleme sayısı."""
        return self._stats[
            "rebalances_done"
        ]

    def construct_portfolio(
        self,
        name: str,
        strategy: str = "balanced",
        holdings: list[dict[str, Any]]
        | None = None,
    ) -> dict[str, Any]:
        """Portföy oluşturur.

        Args:
            name: Portföy adı.
            strategy: Strateji.
            holdings: Varlıklar
                [{name, weight, return_pct}].

        Returns:
            Portföy bilgisi.
        """
        if holdings is None:
            holdings = []

        pid = f"pf_{str(uuid4())[:8]}"
        total_weight = sum(
            h.get("weight", 0)
            for h in holdings
        )
        expected_return = round(
            sum(
                h.get("weight", 0)
                * h.get("return_pct", 0)
                for h in holdings
            )
            / max(total_weight, 0.01),
            2,
        )

        self._portfolios[pid] = {
            "name": name,
            "strategy": strategy,
            "holdings": holdings,
        }
        self._stats[
            "portfolios_created"
        ] += 1

        return {
            "portfolio_id": pid,
            "name": name,
            "strategy": strategy,
            "holding_count": len(holdings),
            "expected_return": (
                expected_return
            ),
            "constructed": True,
        }

    def analyze_diversification(
        self,
        holdings: list[dict[str, Any]]
        | None = None,
    ) -> dict[str, Any]:
        """Çeşitlendirme analizi yapar.

        Args:
            holdings: Varlıklar
                [{name, weight, sector}].

        Returns:
            Çeşitlendirme bilgisi.
        """
        if holdings is None:
            holdings = []

        sectors: dict[str, float] = {}
        for h in holdings:
            sec = h.get("sector", "other")
            sectors[sec] = (
                sectors.get(sec, 0)
                + h.get("weight", 0)
            )

        max_concentration = (
            max(sectors.values())
            if sectors
            else 0
        )

        if max_concentration >= 0.5:
            diversity = "poor"
        elif max_concentration >= 0.3:
            diversity = "moderate"
        else:
            diversity = "good"

        return {
            "sector_count": len(sectors),
            "sectors": sectors,
            "max_concentration": round(
                max_concentration, 2,
            ),
            "diversity_level": diversity,
            "analyzed": True,
        }

    def rebalance(
        self,
        portfolio_id: str,
        current_weights: dict[str, float]
        | None = None,
        target_weights: dict[str, float]
        | None = None,
    ) -> dict[str, Any]:
        """Yeniden dengeleme yapar.

        Args:
            portfolio_id: Portföy kimliği.
            current_weights: Mevcut ağırlıklar.
            target_weights: Hedef ağırlıklar.

        Returns:
            Dengeleme bilgisi.
        """
        if current_weights is None:
            current_weights = {}
        if target_weights is None:
            target_weights = {}

        trades = {}
        for asset in set(
            list(current_weights.keys())
            + list(target_weights.keys()),
        ):
            current = current_weights.get(
                asset, 0,
            )
            target = target_weights.get(
                asset, 0,
            )
            diff = round(
                target - current, 3,
            )
            if abs(diff) > 0.01:
                trades[asset] = {
                    "current": current,
                    "target": target,
                    "action": (
                        "buy"
                        if diff > 0
                        else "sell"
                    ),
                    "amount": abs(diff),
                }

        self._stats[
            "rebalances_done"
        ] += 1

        return {
            "portfolio_id": portfolio_id,
            "trades": trades,
            "trade_count": len(trades),
            "rebalanced": True,
        }

    def manage_risk(
        self,
        portfolio_id: str,
        portfolio_risk: float = 0.5,
        max_risk: float = 0.7,
    ) -> dict[str, Any]:
        """Risk yönetimi yapar.

        Args:
            portfolio_id: Portföy kimliği.
            portfolio_risk: Portföy riski.
            max_risk: Maksimum risk.

        Returns:
            Risk yönetimi bilgisi.
        """
        within_tolerance = (
            portfolio_risk <= max_risk
        )
        excess = round(
            max(
                portfolio_risk - max_risk,
                0,
            ),
            3,
        )

        if within_tolerance:
            action = "maintain"
        elif excess <= 0.1:
            action = "minor_adjustment"
        else:
            action = "significant_reduction"

        return {
            "portfolio_id": portfolio_id,
            "portfolio_risk": (
                portfolio_risk
            ),
            "max_risk": max_risk,
            "within_tolerance": (
                within_tolerance
            ),
            "excess_risk": excess,
            "action": action,
            "managed": True,
        }

    def track_performance(
        self,
        portfolio_id: str,
        period_returns: list[float]
        | None = None,
        benchmark_return: float = 0.0,
    ) -> dict[str, Any]:
        """Performans takip eder.

        Args:
            portfolio_id: Portföy kimliği.
            period_returns: Dönem getirileri.
            benchmark_return: Referans getiri.

        Returns:
            Performans bilgisi.
        """
        if period_returns is None:
            period_returns = []

        if not period_returns:
            return {
                "portfolio_id": (
                    portfolio_id
                ),
                "tracked": False,
            }

        avg_return = round(
            sum(period_returns)
            / len(period_returns),
            2,
        )
        alpha = round(
            avg_return - benchmark_return,
            2,
        )

        if alpha > 0:
            performance = "outperforming"
        elif alpha == 0:
            performance = "matching"
        else:
            performance = "underperforming"

        return {
            "portfolio_id": portfolio_id,
            "avg_return": avg_return,
            "benchmark": benchmark_return,
            "alpha": alpha,
            "performance": performance,
            "tracked": True,
        }
