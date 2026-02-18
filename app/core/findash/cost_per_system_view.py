"""
Sistem basina maliyet modulu.

Sistem maliyet takibi, API maliyetleri,
altyapi maliyetleri, optimizasyon onerileri,
trend analizi.
"""

import logging
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)


class CostPerSystemView:
    """Sistem basina maliyet gorunumu.

    Attributes:
        _costs: Maliyet kayitlari.
        _stats: Istatistikler.
    """

    def __init__(self) -> None:
        """Gorunumu baslatir."""
        self._costs: list[dict] = []
        self._stats: dict[str, int] = {
            "costs_recorded": 0,
            "optimizations_suggested": 0,
        }
        logger.info(
            "CostPerSystemView baslatildi"
        )

    @property
    def cost_count(self) -> int:
        """Maliyet sayisi."""
        return len(self._costs)

    def record_cost(
        self,
        system_name: str = "",
        cost_type: str = "api",
        amount: float = 0.0,
        period: str = "",
        details: str = "",
    ) -> dict[str, Any]:
        """Maliyet kaydeder.

        Args:
            system_name: Sistem adi.
            cost_type: Maliyet turu.
            amount: Tutar.
            period: Donem.
            details: Detaylar.

        Returns:
            Kayit bilgisi.
        """
        try:
            cid = f"cs_{uuid4()!s:.8}"
            cost = {
                "cost_id": cid,
                "system_name": system_name,
                "cost_type": cost_type,
                "amount": amount,
                "period": period,
                "details": details,
                "timestamp": datetime.now(
                    timezone.utc
                ).isoformat(),
            }
            self._costs.append(cost)
            self._stats[
                "costs_recorded"
            ] += 1

            return {
                "cost_id": cid,
                "system_name": system_name,
                "amount": amount,
                "recorded": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "recorded": False,
                "error": str(e),
            }

    def get_system_costs(
        self,
    ) -> dict[str, Any]:
        """Sistem bazli maliyetleri getirir.

        Returns:
            Maliyet dagilimi.
        """
        try:
            systems: dict[
                str, float
            ] = {}
            for c in self._costs:
                sys = c.get(
                    "system_name", "unknown"
                )
                systems[sys] = (
                    systems.get(sys, 0.0)
                    + c["amount"]
                )

            total = sum(systems.values())
            breakdown = [
                {
                    "system": sys,
                    "total_cost": round(
                        amt, 2
                    ),
                    "percentage": round(
                        (amt / total * 100)
                        if total > 0
                        else 0,
                        1,
                    ),
                }
                for sys, amt in sorted(
                    systems.items(),
                    key=lambda x: x[1],
                    reverse=True,
                )
            ]

            return {
                "systems": breakdown,
                "system_count": len(
                    breakdown
                ),
                "total_cost": round(
                    total, 2
                ),
                "retrieved": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "retrieved": False,
                "error": str(e),
            }

    def get_api_costs(
        self,
    ) -> dict[str, Any]:
        """API maliyetlerini getirir.

        Returns:
            API maliyet bilgisi.
        """
        try:
            api_costs = [
                c
                for c in self._costs
                if c["cost_type"] == "api"
            ]

            systems: dict[
                str, float
            ] = {}
            for c in api_costs:
                sys = c["system_name"]
                systems[sys] = (
                    systems.get(sys, 0.0)
                    + c["amount"]
                )

            total = sum(systems.values())

            return {
                "api_costs": [
                    {
                        "system": sys,
                        "cost": round(amt, 2),
                    }
                    for sys, amt in sorted(
                        systems.items(),
                        key=lambda x: x[1],
                        reverse=True,
                    )
                ],
                "total_api_cost": round(
                    total, 2
                ),
                "retrieved": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "retrieved": False,
                "error": str(e),
            }

    def get_infrastructure_costs(
        self,
    ) -> dict[str, Any]:
        """Altyapi maliyetlerini getirir.

        Returns:
            Altyapi maliyet bilgisi.
        """
        try:
            infra_costs = [
                c
                for c in self._costs
                if c["cost_type"]
                == "infrastructure"
            ]

            systems: dict[
                str, float
            ] = {}
            for c in infra_costs:
                sys = c["system_name"]
                systems[sys] = (
                    systems.get(sys, 0.0)
                    + c["amount"]
                )

            total = sum(systems.values())

            return {
                "infra_costs": [
                    {
                        "system": sys,
                        "cost": round(amt, 2),
                    }
                    for sys, amt in sorted(
                        systems.items(),
                        key=lambda x: x[1],
                        reverse=True,
                    )
                ],
                "total_infra_cost": round(
                    total, 2
                ),
                "retrieved": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "retrieved": False,
                "error": str(e),
            }

    def suggest_optimizations(
        self,
        threshold_pct: float = 20.0,
    ) -> dict[str, Any]:
        """Optimizasyon onerileri getirir.

        Args:
            threshold_pct: Esik yuzdesi.

        Returns:
            Oneri bilgisi.
        """
        try:
            sys_costs = (
                self.get_system_costs()
            )
            systems = sys_costs.get(
                "systems", []
            )

            suggestions = []
            for sys in systems:
                if (
                    sys["percentage"]
                    > threshold_pct
                ):
                    suggestions.append({
                        "system": sys[
                            "system"
                        ],
                        "current_cost": sys[
                            "total_cost"
                        ],
                        "percentage": sys[
                            "percentage"
                        ],
                        "suggestion": (
                            "Yuksek maliyet "
                            "orani, "
                            "optimizasyon "
                            "gerekli"
                        ),
                        "priority": (
                            "high"
                            if sys[
                                "percentage"
                            ]
                            > 30
                            else "medium"
                        ),
                    })

            sys_trends: dict[
                str, list[float]
            ] = {}
            for c in self._costs:
                sys = c["system_name"]
                if sys not in sys_trends:
                    sys_trends[sys] = []
                sys_trends[sys].append(
                    c["amount"]
                )

            for sys, vals in (
                sys_trends.items()
            ):
                if len(vals) >= 3:
                    recent = vals[-3:]
                    if all(
                        recent[i]
                        < recent[i + 1]
                        for i in range(
                            len(recent) - 1
                        )
                    ):
                        suggestions.append({
                            "system": sys,
                            "suggestion": (
                                "Artan maliyet "
                                "trendi tespit "
                                "edildi"
                            ),
                            "priority": (
                                "medium"
                            ),
                        })

            self._stats[
                "optimizations_suggested"
            ] += len(suggestions)

            return {
                "suggestions": suggestions,
                "suggestion_count": len(
                    suggestions
                ),
                "suggested": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "suggested": False,
                "error": str(e),
            }

    def get_cost_trend(
        self,
        system_name: str = "",
    ) -> dict[str, Any]:
        """Maliyet trendi getirir.

        Args:
            system_name: Sistem adi.

        Returns:
            Trend bilgisi.
        """
        try:
            costs = [
                c
                for c in self._costs
                if c["system_name"]
                == system_name
            ]

            periods: dict[
                str, float
            ] = {}
            for c in costs:
                period = c.get(
                    "period", "unknown"
                )
                periods[period] = (
                    periods.get(period, 0.0)
                    + c["amount"]
                )

            sorted_p = sorted(
                periods.items()
            )
            values = [v for _, v in sorted_p]

            if len(values) < 2:
                direction = (
                    "insufficient_data"
                )
            else:
                avg_change = (
                    values[-1] - values[0]
                ) / (len(values) - 1)
                if avg_change > 0:
                    direction = "increasing"
                elif avg_change < 0:
                    direction = "decreasing"
                else:
                    direction = "stable"

            return {
                "system_name": system_name,
                "periods": [
                    {
                        "period": p,
                        "cost": round(v, 2),
                    }
                    for p, v in sorted_p
                ],
                "direction": direction,
                "retrieved": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "retrieved": False,
                "error": str(e),
            }
