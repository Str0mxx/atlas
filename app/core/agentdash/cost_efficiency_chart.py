"""
Maliyet verimliligi modulu.

Gorev basina maliyet, kaynak kullanimi,
optimizasyon takibi, karsilastirma,
tasarruf hesaplama.
"""

import logging
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)


class CostEfficiencyChart:
    """Maliyet verimliligi grafigi.

    Attributes:
        _costs: Maliyet kayitlari.
        _stats: Istatistikler.
    """

    def __init__(self) -> None:
        """Grafigi baslatir."""
        self._costs: list[dict] = []
        self._stats: dict[str, int] = {
            "costs_recorded": 0,
            "optimizations_found": 0,
        }
        logger.info(
            "CostEfficiencyChart baslatildi"
        )

    @property
    def cost_count(self) -> int:
        """Maliyet kayit sayisi."""
        return len(self._costs)

    def record_cost(
        self,
        agent_id: str = "",
        task_id: str = "",
        api_cost: float = 0.0,
        compute_cost: float = 0.0,
        duration_ms: int = 0,
        success: bool = True,
        period: str = "",
    ) -> dict[str, Any]:
        """Maliyet kaydeder.

        Args:
            agent_id: Agent ID.
            task_id: Gorev ID.
            api_cost: API maliyeti.
            compute_cost: Islem maliyeti.
            duration_ms: Sure (ms).
            success: Basarili mi.
            period: Donem.

        Returns:
            Kayit bilgisi.
        """
        try:
            cid = f"ce_{uuid4()!s:.8}"
            total = api_cost + compute_cost
            cost = {
                "cost_id": cid,
                "agent_id": agent_id,
                "task_id": task_id,
                "api_cost": api_cost,
                "compute_cost": compute_cost,
                "total_cost": round(total, 4),
                "duration_ms": duration_ms,
                "success": success,
                "period": period,
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
                "total_cost": round(total, 4),
                "recorded": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "recorded": False,
                "error": str(e),
            }

    def get_cost_per_task(
        self,
        agent_id: str = "",
    ) -> dict[str, Any]:
        """Gorev basina maliyet getirir.

        Args:
            agent_id: Agent ID.

        Returns:
            Maliyet bilgisi.
        """
        try:
            costs = [
                c
                for c in self._costs
                if not agent_id
                or c["agent_id"] == agent_id
            ]

            if not costs:
                return {
                    "avg_cost": 0.0,
                    "retrieved": True,
                }

            totals = [
                c["total_cost"] for c in costs
            ]
            avg = sum(totals) / len(totals)
            successful = [
                c["total_cost"]
                for c in costs
                if c["success"]
            ]
            avg_success = (
                sum(successful)
                / len(successful)
                if successful
                else 0
            )

            return {
                "agent_id": agent_id or "all",
                "total_tasks": len(costs),
                "total_cost": round(
                    sum(totals), 4
                ),
                "avg_cost": round(avg, 4),
                "avg_successful_cost": round(
                    avg_success, 4
                ),
                "min_cost": round(
                    min(totals), 4
                ),
                "max_cost": round(
                    max(totals), 4
                ),
                "retrieved": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "retrieved": False,
                "error": str(e),
            }

    def get_resource_usage(
        self,
    ) -> dict[str, Any]:
        """Kaynak kullanimini getirir.

        Returns:
            Kaynak kullanim bilgisi.
        """
        try:
            agents: dict[
                str, dict[str, float]
            ] = {}
            for c in self._costs:
                aid = c["agent_id"]
                if aid not in agents:
                    agents[aid] = {
                        "api_cost": 0.0,
                        "compute_cost": 0.0,
                        "total_cost": 0.0,
                        "task_count": 0,
                    }
                agents[aid][
                    "api_cost"
                ] += c["api_cost"]
                agents[aid][
                    "compute_cost"
                ] += c["compute_cost"]
                agents[aid][
                    "total_cost"
                ] += c["total_cost"]
                agents[aid]["task_count"] += 1

            total_all = sum(
                d["total_cost"]
                for d in agents.values()
            )

            usage = [
                {
                    "agent_id": aid,
                    "api_cost": round(
                        d["api_cost"], 4
                    ),
                    "compute_cost": round(
                        d["compute_cost"], 4
                    ),
                    "total_cost": round(
                        d["total_cost"], 4
                    ),
                    "task_count": int(
                        d["task_count"]
                    ),
                    "percentage": round(
                        d["total_cost"]
                        / total_all
                        * 100,
                        1,
                    )
                    if total_all > 0
                    else 0,
                }
                for aid, d in sorted(
                    agents.items(),
                    key=lambda x: x[1][
                        "total_cost"
                    ],
                    reverse=True,
                )
            ]

            return {
                "usage": usage,
                "total_cost": round(
                    total_all, 4
                ),
                "agent_count": len(usage),
                "retrieved": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "retrieved": False,
                "error": str(e),
            }

    def track_optimization(
        self,
    ) -> dict[str, Any]:
        """Optimizasyon takibi yapar.

        Returns:
            Optimizasyon bilgisi.
        """
        try:
            agents: dict[
                str, list[float]
            ] = {}
            for c in self._costs:
                aid = c["agent_id"]
                if aid not in agents:
                    agents[aid] = []
                agents[aid].append(
                    c["total_cost"]
                )

            optimizations = []
            for aid, costs in agents.items():
                if len(costs) < 3:
                    continue
                recent = costs[-3:]
                earlier = costs[:-3] or costs[:1]
                avg_recent = sum(recent) / len(
                    recent
                )
                avg_earlier = sum(earlier) / len(
                    earlier
                )

                if avg_earlier > 0:
                    change_pct = (
                        (
                            avg_recent
                            - avg_earlier
                        )
                        / avg_earlier
                        * 100
                    )
                else:
                    change_pct = 0

                if change_pct < -10:
                    status = "improving"
                elif change_pct > 10:
                    status = "degrading"
                else:
                    status = "stable"

                optimizations.append({
                    "agent_id": aid,
                    "avg_recent_cost": round(
                        avg_recent, 4
                    ),
                    "avg_earlier_cost": round(
                        avg_earlier, 4
                    ),
                    "change_pct": round(
                        change_pct, 1
                    ),
                    "status": status,
                })

            self._stats[
                "optimizations_found"
            ] += len(
                [
                    o
                    for o in optimizations
                    if o["status"] == "improving"
                ]
            )

            return {
                "optimizations": optimizations,
                "tracked": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "tracked": False,
                "error": str(e),
            }

    def compare_efficiency(
        self,
    ) -> dict[str, Any]:
        """Verimlilik karsilastirir.

        Returns:
            Karsilastirma bilgisi.
        """
        try:
            agents: dict[
                str, dict
            ] = {}
            for c in self._costs:
                aid = c["agent_id"]
                if aid not in agents:
                    agents[aid] = {
                        "total_cost": 0.0,
                        "successful": 0,
                        "total": 0,
                    }
                agents[aid][
                    "total_cost"
                ] += c["total_cost"]
                agents[aid]["total"] += 1
                if c["success"]:
                    agents[aid][
                        "successful"
                    ] += 1

            comparisons = []
            for aid, d in agents.items():
                cost_per_success = (
                    d["total_cost"]
                    / d["successful"]
                    if d["successful"] > 0
                    else d["total_cost"]
                )
                efficiency = (
                    d["successful"]
                    / d["total"]
                    * 100
                    / (
                        d["total_cost"]
                        / d["total"]
                    )
                    if d["total"] > 0
                    and d["total_cost"] > 0
                    else 0
                )
                comparisons.append({
                    "agent_id": aid,
                    "total_cost": round(
                        d["total_cost"], 4
                    ),
                    "cost_per_success": round(
                        cost_per_success, 4
                    ),
                    "efficiency_score": round(
                        efficiency, 1
                    ),
                })

            comparisons.sort(
                key=lambda x: x[
                    "efficiency_score"
                ],
                reverse=True,
            )

            return {
                "comparisons": comparisons,
                "compared": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "compared": False,
                "error": str(e),
            }

    def calculate_savings(
        self,
        baseline_cost: float = 0.0,
    ) -> dict[str, Any]:
        """Tasarruf hesaplar.

        Args:
            baseline_cost: Referans maliyet.

        Returns:
            Tasarruf bilgisi.
        """
        try:
            if not self._costs:
                return {
                    "total_savings": 0.0,
                    "calculated": True,
                }

            actual_total = sum(
                c["total_cost"]
                for c in self._costs
            )
            task_count = len(self._costs)
            baseline_total = (
                baseline_cost * task_count
            )
            savings = (
                baseline_total - actual_total
            )

            return {
                "baseline_cost_per_task": (
                    baseline_cost
                ),
                "actual_avg_cost": round(
                    actual_total / task_count, 4
                ),
                "total_baseline": round(
                    baseline_total, 4
                ),
                "total_actual": round(
                    actual_total, 4
                ),
                "total_savings": round(
                    savings, 4
                ),
                "savings_pct": round(
                    savings
                    / baseline_total
                    * 100,
                    1,
                )
                if baseline_total > 0
                else 0,
                "calculated": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "calculated": False,
                "error": str(e),
            }
