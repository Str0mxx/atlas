"""
Gider dagilimi modulu.

Kategori dagilimi, pasta/cubuk grafik,
trend analizi, en yuksek giderler,
anomali vurgulama.
"""

import logging
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)


class ExpenseBreakdown:
    """Gider dagilimi.

    Attributes:
        _expenses: Gider kayitlari.
        _stats: Istatistikler.
    """

    def __init__(self) -> None:
        """Dagilimi baslatir."""
        self._expenses: list[dict] = []
        self._stats: dict[str, int] = {
            "expenses_recorded": 0,
            "anomalies_detected": 0,
        }
        logger.info(
            "ExpenseBreakdown baslatildi"
        )

    @property
    def expense_count(self) -> int:
        """Gider sayisi."""
        return len(self._expenses)

    def record_expense(
        self,
        amount: float = 0.0,
        category: str = "operational",
        description: str = "",
        period: str = "",
        recurring: bool = False,
    ) -> dict[str, Any]:
        """Gider kaydeder.

        Args:
            amount: Tutar.
            category: Kategori.
            description: Aciklama.
            period: Donem.
            recurring: Tekrarli mi.

        Returns:
            Kayit bilgisi.
        """
        try:
            eid = f"ep_{uuid4()!s:.8}"
            expense = {
                "expense_id": eid,
                "amount": amount,
                "category": category,
                "description": description,
                "period": period,
                "recurring": recurring,
                "timestamp": datetime.now(
                    timezone.utc
                ).isoformat(),
            }
            self._expenses.append(expense)
            self._stats[
                "expenses_recorded"
            ] += 1

            return {
                "expense_id": eid,
                "amount": amount,
                "category": category,
                "recorded": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "recorded": False,
                "error": str(e),
            }

    def get_category_breakdown(
        self,
    ) -> dict[str, Any]:
        """Kategori dagilimi getirir.

        Returns:
            Dagilim bilgisi.
        """
        try:
            categories: dict[
                str, float
            ] = {}
            for exp in self._expenses:
                cat = exp.get(
                    "category", "other"
                )
                categories[cat] = (
                    categories.get(cat, 0.0)
                    + exp["amount"]
                )

            total = sum(categories.values())
            breakdown = [
                {
                    "category": cat,
                    "amount": round(amt, 2),
                    "percentage": round(
                        (amt / total * 100)
                        if total > 0
                        else 0,
                        1,
                    ),
                }
                for cat, amt in sorted(
                    categories.items(),
                    key=lambda x: x[1],
                    reverse=True,
                )
            ]

            return {
                "breakdown": breakdown,
                "category_count": len(
                    breakdown
                ),
                "total_expenses": round(
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

    def get_trend(
        self,
    ) -> dict[str, Any]:
        """Trend analizi yapar.

        Returns:
            Trend bilgisi.
        """
        try:
            periods: dict[str, float] = {}
            for exp in self._expenses:
                period = exp.get(
                    "period", "unknown"
                )
                periods[period] = (
                    periods.get(period, 0.0)
                    + exp["amount"]
                )

            sorted_p = sorted(periods.items())
            values = [v for _, v in sorted_p]

            if len(values) < 2:
                return {
                    "trend": (
                        "insufficient_data"
                    ),
                    "analyzed": True,
                }

            avg_change = sum(
                values[i] - values[i - 1]
                for i in range(1, len(values))
            ) / (len(values) - 1)

            if avg_change > 0:
                direction = "increasing"
            elif avg_change < 0:
                direction = "decreasing"
            else:
                direction = "stable"

            return {
                "periods": [
                    {
                        "period": p,
                        "amount": round(v, 2),
                    }
                    for p, v in sorted_p
                ],
                "avg_change": round(
                    avg_change, 2
                ),
                "direction": direction,
                "total_periods": len(
                    sorted_p
                ),
                "analyzed": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "analyzed": False,
                "error": str(e),
            }

    def get_top_expenses(
        self,
        limit: int = 10,
    ) -> dict[str, Any]:
        """En yuksek giderleri getirir.

        Args:
            limit: Sonuc limiti.

        Returns:
            Gider listesi.
        """
        try:
            sorted_exp = sorted(
                self._expenses,
                key=lambda x: x.get(
                    "amount", 0
                ),
                reverse=True,
            )[:limit]

            return {
                "top_expenses": [
                    {
                        "expense_id": e[
                            "expense_id"
                        ],
                        "amount": e["amount"],
                        "category": e[
                            "category"
                        ],
                        "description": e[
                            "description"
                        ],
                    }
                    for e in sorted_exp
                ],
                "count": len(sorted_exp),
                "retrieved": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "retrieved": False,
                "error": str(e),
            }

    def detect_anomalies(
        self,
        threshold_multiplier: float = 2.0,
    ) -> dict[str, Any]:
        """Anomali tespit eder.

        Args:
            threshold_multiplier: Esik carpani.

        Returns:
            Anomali bilgisi.
        """
        try:
            cat_amounts: dict[
                str, list[float]
            ] = {}
            for exp in self._expenses:
                cat = exp.get(
                    "category", "other"
                )
                if cat not in cat_amounts:
                    cat_amounts[cat] = []
                cat_amounts[cat].append(
                    exp["amount"]
                )

            anomalies = []
            for cat, amounts in (
                cat_amounts.items()
            ):
                if len(amounts) < 2:
                    continue

                avg = sum(amounts) / len(
                    amounts
                )
                threshold = (
                    avg * threshold_multiplier
                )

                for exp in self._expenses:
                    if (
                        exp.get("category")
                        == cat
                        and exp["amount"]
                        > threshold
                    ):
                        anomalies.append({
                            "expense_id": exp[
                                "expense_id"
                            ],
                            "amount": exp[
                                "amount"
                            ],
                            "category": cat,
                            "average": round(
                                avg, 2
                            ),
                            "threshold": round(
                                threshold, 2
                            ),
                            "deviation": round(
                                exp["amount"]
                                / avg,
                                1,
                            ),
                        })

            self._stats[
                "anomalies_detected"
            ] += len(anomalies)

            return {
                "anomalies": anomalies,
                "anomaly_count": len(
                    anomalies
                ),
                "threshold_multiplier": (
                    threshold_multiplier
                ),
                "detected": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "detected": False,
                "error": str(e),
            }
