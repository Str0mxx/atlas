"""
Performans karsilastirma modulu.

Yan yana karsilastirma, metrik karsilastirma,
donem karsilastirma, bosluk analizi,
gorsellestirme.
"""

import logging
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)


class PerformanceComparison:
    """Performans karsilastirma.

    Attributes:
        _records: Performans kayitlari.
        _stats: Istatistikler.
    """

    def __init__(self) -> None:
        """Karsilastirmayi baslatir."""
        self._records: list[dict] = []
        self._stats: dict[str, int] = {
            "records_added": 0,
            "comparisons_made": 0,
        }
        logger.info(
            "PerformanceComparison baslatildi"
        )

    @property
    def record_count(self) -> int:
        """Kayit sayisi."""
        return len(self._records)

    def add_record(
        self,
        agent_id: str = "",
        metric: str = "performance",
        value: float = 0.0,
        period: str = "",
        category: str = "general",
    ) -> dict[str, Any]:
        """Kayit ekler.

        Args:
            agent_id: Agent ID.
            metric: Metrik adi.
            value: Deger.
            period: Donem.
            category: Kategori.

        Returns:
            Ekleme bilgisi.
        """
        try:
            rid = f"pc_{uuid4()!s:.8}"
            record = {
                "record_id": rid,
                "agent_id": agent_id,
                "metric": metric,
                "value": value,
                "period": period,
                "category": category,
                "timestamp": datetime.now(
                    timezone.utc
                ).isoformat(),
            }
            self._records.append(record)
            self._stats["records_added"] += 1

            return {
                "record_id": rid,
                "agent_id": agent_id,
                "added": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "added": False,
                "error": str(e),
            }

    def compare_side_by_side(
        self,
        agent_ids: list[str] | None = None,
    ) -> dict[str, Any]:
        """Yan yana karsilastirir.

        Args:
            agent_ids: Karsilastirilacak agentlar.

        Returns:
            Karsilastirma bilgisi.
        """
        try:
            if not agent_ids:
                agent_ids = list({
                    r["agent_id"]
                    for r in self._records
                })

            comparison = {}
            for aid in agent_ids:
                recs = [
                    r
                    for r in self._records
                    if r["agent_id"] == aid
                ]
                if not recs:
                    continue

                metrics: dict[
                    str, list[float]
                ] = {}
                for r in recs:
                    m = r["metric"]
                    if m not in metrics:
                        metrics[m] = []
                    metrics[m].append(
                        r["value"]
                    )

                comparison[aid] = {
                    metric: {
                        "avg": round(
                            sum(vals)
                            / len(vals),
                            2,
                        ),
                        "min": round(
                            min(vals), 2
                        ),
                        "max": round(
                            max(vals), 2
                        ),
                        "count": len(vals),
                    }
                    for metric, vals
                    in metrics.items()
                }

            self._stats[
                "comparisons_made"
            ] += 1

            return {
                "comparison": comparison,
                "agent_count": len(comparison),
                "compared": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "compared": False,
                "error": str(e),
            }

    def compare_metric(
        self,
        metric: str = "performance",
    ) -> dict[str, Any]:
        """Metrik karsilastirir.

        Args:
            metric: Karsilastirilacak metrik.

        Returns:
            Metrik karsilastirma bilgisi.
        """
        try:
            recs = [
                r
                for r in self._records
                if r["metric"] == metric
            ]

            agents: dict[
                str, list[float]
            ] = {}
            for r in recs:
                aid = r["agent_id"]
                if aid not in agents:
                    agents[aid] = []
                agents[aid].append(r["value"])

            results = []
            for aid, vals in agents.items():
                avg = sum(vals) / len(vals)
                results.append({
                    "agent_id": aid,
                    "avg_value": round(avg, 2),
                    "min_value": round(
                        min(vals), 2
                    ),
                    "max_value": round(
                        max(vals), 2
                    ),
                    "count": len(vals),
                })

            results.sort(
                key=lambda x: x["avg_value"],
                reverse=True,
            )

            return {
                "metric": metric,
                "results": results,
                "compared": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "compared": False,
                "error": str(e),
            }

    def compare_periods(
        self,
        agent_id: str = "",
        period_a: str = "",
        period_b: str = "",
    ) -> dict[str, Any]:
        """Donem karsilastirir.

        Args:
            agent_id: Agent ID.
            period_a: Ilk donem.
            period_b: Ikinci donem.

        Returns:
            Donem karsilastirma bilgisi.
        """
        try:
            recs_a = [
                r
                for r in self._records
                if (
                    not agent_id
                    or r["agent_id"] == agent_id
                )
                and r["period"] == period_a
            ]
            recs_b = [
                r
                for r in self._records
                if (
                    not agent_id
                    or r["agent_id"] == agent_id
                )
                and r["period"] == period_b
            ]

            avg_a = (
                sum(r["value"] for r in recs_a)
                / len(recs_a)
                if recs_a
                else 0
            )
            avg_b = (
                sum(r["value"] for r in recs_b)
                / len(recs_b)
                if recs_b
                else 0
            )
            change = avg_b - avg_a
            change_pct = (
                change / avg_a * 100
                if avg_a > 0
                else 0
            )

            return {
                "agent_id": agent_id or "all",
                "period_a": {
                    "period": period_a,
                    "avg_value": round(
                        avg_a, 2
                    ),
                    "count": len(recs_a),
                },
                "period_b": {
                    "period": period_b,
                    "avg_value": round(
                        avg_b, 2
                    ),
                    "count": len(recs_b),
                },
                "change": round(change, 2),
                "change_pct": round(
                    change_pct, 1
                ),
                "compared": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "compared": False,
                "error": str(e),
            }

    def analyze_gaps(
        self,
    ) -> dict[str, Any]:
        """Bosluk analizi yapar.

        Returns:
            Bosluk bilgisi.
        """
        try:
            agents: dict[
                str, list[float]
            ] = {}
            for r in self._records:
                aid = r["agent_id"]
                if aid not in agents:
                    agents[aid] = []
                agents[aid].append(r["value"])

            if len(agents) < 2:
                return {
                    "gaps": [],
                    "analyzed": True,
                }

            avgs = {
                aid: sum(vals) / len(vals)
                for aid, vals in agents.items()
            }

            sorted_agents = sorted(
                avgs.items(),
                key=lambda x: x[1],
                reverse=True,
            )
            best_id, best_avg = (
                sorted_agents[0]
            )

            gaps = []
            for aid, avg in sorted_agents[1:]:
                gap = best_avg - avg
                gap_pct = (
                    gap / best_avg * 100
                    if best_avg > 0
                    else 0
                )
                gaps.append({
                    "agent_id": aid,
                    "avg_score": round(avg, 2),
                    "gap": round(gap, 2),
                    "gap_pct": round(
                        gap_pct, 1
                    ),
                    "vs_best": best_id,
                })

            return {
                "best_agent": best_id,
                "best_avg": round(
                    best_avg, 2
                ),
                "gaps": gaps,
                "analyzed": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "analyzed": False,
                "error": str(e),
            }

    def get_visualization_data(
        self,
        metric: str = "",
    ) -> dict[str, Any]:
        """Gorsellestirme verisi getirir.

        Args:
            metric: Metrik filtresi.

        Returns:
            Gorsellestirme bilgisi.
        """
        try:
            recs = (
                [
                    r
                    for r in self._records
                    if r["metric"] == metric
                ]
                if metric
                else self._records
            )

            agents: dict[
                str, dict[str, list]
            ] = {}
            for r in recs:
                aid = r["agent_id"]
                if aid not in agents:
                    agents[aid] = {
                        "periods": [],
                        "values": [],
                    }
                agents[aid]["periods"].append(
                    r["period"]
                )
                agents[aid]["values"].append(
                    r["value"]
                )

            series = [
                {
                    "agent_id": aid,
                    "data_points": len(
                        data["values"]
                    ),
                    "periods": data["periods"],
                    "values": data["values"],
                }
                for aid, data in agents.items()
            ]

            return {
                "series": series,
                "metric": metric or "all",
                "retrieved": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "retrieved": False,
                "error": str(e),
            }
