"""
Gelir grafigi modulu.

Gelir gorsellestirme, zaman serisi,
kaynak bazli dagilim, buyume gostergeleri,
donem karsilastirma.
"""

import logging
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)


class RevenueChart:
    """Gelir grafigi.

    Attributes:
        _entries: Gelir kayitlari.
        _stats: Istatistikler.
    """

    def __init__(self) -> None:
        """Grafigi baslatir."""
        self._entries: list[dict] = []
        self._stats: dict[str, int] = {
            "entries_recorded": 0,
            "charts_generated": 0,
        }
        logger.info(
            "RevenueChart baslatildi"
        )

    @property
    def entry_count(self) -> int:
        """Kayit sayisi."""
        return len(self._entries)

    def record_revenue(
        self,
        amount: float = 0.0,
        source: str = "",
        category: str = "sales",
        period: str = "",
        currency: str = "TRY",
    ) -> dict[str, Any]:
        """Gelir kaydeder.

        Args:
            amount: Tutar.
            source: Kaynak.
            category: Kategori.
            period: Donem.
            currency: Para birimi.

        Returns:
            Kayit bilgisi.
        """
        try:
            rid = f"rv_{uuid4()!s:.8}"
            entry = {
                "entry_id": rid,
                "amount": amount,
                "source": source,
                "category": category,
                "period": period,
                "currency": currency,
                "timestamp": datetime.now(
                    timezone.utc
                ).isoformat(),
            }
            self._entries.append(entry)
            self._stats[
                "entries_recorded"
            ] += 1

            return {
                "entry_id": rid,
                "amount": amount,
                "source": source,
                "recorded": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "recorded": False,
                "error": str(e),
            }

    def get_time_series(
        self,
        period_type: str = "monthly",
    ) -> dict[str, Any]:
        """Zaman serisi getirir.

        Args:
            period_type: Donem turu.

        Returns:
            Zaman serisi.
        """
        try:
            periods: dict[str, float] = {}
            for entry in self._entries:
                period = entry.get(
                    "period", "unknown"
                )
                periods[period] = (
                    periods.get(period, 0.0)
                    + entry["amount"]
                )

            sorted_periods = sorted(
                periods.items()
            )

            return {
                "period_type": period_type,
                "data_points": [
                    {
                        "period": p,
                        "revenue": round(v, 2),
                    }
                    for p, v in sorted_periods
                ],
                "total_periods": len(
                    sorted_periods
                ),
                "total_revenue": round(
                    sum(periods.values()), 2
                ),
                "retrieved": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "retrieved": False,
                "error": str(e),
            }

    def get_breakdown_by_source(
        self,
    ) -> dict[str, Any]:
        """Kaynak bazli dagilim getirir.

        Returns:
            Dagilim bilgisi.
        """
        try:
            sources: dict[str, float] = {}
            for entry in self._entries:
                src = entry.get(
                    "source", "unknown"
                )
                sources[src] = (
                    sources.get(src, 0.0)
                    + entry["amount"]
                )

            total = sum(sources.values())
            breakdown = [
                {
                    "source": src,
                    "amount": round(amt, 2),
                    "percentage": round(
                        (amt / total * 100)
                        if total > 0
                        else 0,
                        1,
                    ),
                }
                for src, amt in sorted(
                    sources.items(),
                    key=lambda x: x[1],
                    reverse=True,
                )
            ]

            return {
                "breakdown": breakdown,
                "source_count": len(
                    breakdown
                ),
                "total_revenue": round(
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

    def calculate_growth(
        self,
    ) -> dict[str, Any]:
        """Buyume hesaplar.

        Returns:
            Buyume bilgisi.
        """
        try:
            periods: dict[str, float] = {}
            for entry in self._entries:
                period = entry.get(
                    "period", "unknown"
                )
                periods[period] = (
                    periods.get(period, 0.0)
                    + entry["amount"]
                )

            sorted_p = sorted(periods.items())
            if len(sorted_p) < 2:
                return {
                    "growth_rate": 0.0,
                    "trend": "insufficient_data",
                    "calculated": True,
                }

            values = [v for _, v in sorted_p]
            prev = values[-2]
            curr = values[-1]

            growth_rate = (
                ((curr - prev) / prev * 100)
                if prev > 0
                else 0.0
            )

            if growth_rate > 5:
                trend = "growing"
            elif growth_rate < -5:
                trend = "declining"
            else:
                trend = "stable"

            return {
                "current_period": (
                    sorted_p[-1][0]
                ),
                "previous_period": (
                    sorted_p[-2][0]
                ),
                "current_revenue": round(
                    curr, 2
                ),
                "previous_revenue": round(
                    prev, 2
                ),
                "growth_rate": round(
                    growth_rate, 1
                ),
                "trend": trend,
                "calculated": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "calculated": False,
                "error": str(e),
            }

    def compare_periods(
        self,
        period_a: str = "",
        period_b: str = "",
    ) -> dict[str, Any]:
        """Donemleri karsilastirir.

        Args:
            period_a: Ilk donem.
            period_b: Ikinci donem.

        Returns:
            Karsilastirma bilgisi.
        """
        try:
            rev_a = sum(
                e["amount"]
                for e in self._entries
                if e.get("period") == period_a
            )
            rev_b = sum(
                e["amount"]
                for e in self._entries
                if e.get("period") == period_b
            )

            diff = rev_b - rev_a
            pct_change = (
                (diff / rev_a * 100)
                if rev_a > 0
                else 0.0
            )

            return {
                "period_a": period_a,
                "period_b": period_b,
                "revenue_a": round(rev_a, 2),
                "revenue_b": round(rev_b, 2),
                "difference": round(diff, 2),
                "percentage_change": round(
                    pct_change, 1
                ),
                "compared": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "compared": False,
                "error": str(e),
            }

    def generate_chart_data(
        self,
    ) -> dict[str, Any]:
        """Grafik verisi uretir.

        Returns:
            Grafik verisi.
        """
        try:
            ts = self.get_time_series()
            breakdown = (
                self.get_breakdown_by_source()
            )
            growth = self.calculate_growth()

            self._stats[
                "charts_generated"
            ] += 1

            return {
                "time_series": ts.get(
                    "data_points", []
                ),
                "source_breakdown": (
                    breakdown.get(
                        "breakdown", []
                    )
                ),
                "growth": {
                    "rate": growth.get(
                        "growth_rate", 0.0
                    ),
                    "trend": growth.get(
                        "trend", "unknown"
                    ),
                },
                "total_revenue": ts.get(
                    "total_revenue", 0.0
                ),
                "generated": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "generated": False,
                "error": str(e),
            }
