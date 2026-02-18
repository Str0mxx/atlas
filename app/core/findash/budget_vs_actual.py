"""
Butce vs gercek modulu.

Sapma analizi, gorsel karsilastirma,
yuzde takibi, asim uyarisi,
detaya inme.
"""

import logging
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)


class BudgetVsActual:
    """Butce vs gercek karsilastirma.

    Attributes:
        _budgets: Butce kayitlari.
        _actuals: Gercek kayitlar.
        _stats: Istatistikler.
    """

    def __init__(self) -> None:
        """Karsilastirmayi baslatir."""
        self._budgets: list[dict] = []
        self._actuals: list[dict] = []
        self._stats: dict[str, int] = {
            "budgets_set": 0,
            "actuals_recorded": 0,
            "alerts_raised": 0,
        }
        logger.info(
            "BudgetVsActual baslatildi"
        )

    @property
    def budget_count(self) -> int:
        """Butce sayisi."""
        return len(self._budgets)

    @property
    def actual_count(self) -> int:
        """Gercek kayit sayisi."""
        return len(self._actuals)

    def set_budget(
        self,
        category: str = "",
        amount: float = 0.0,
        period: str = "",
    ) -> dict[str, Any]:
        """Butce belirler.

        Args:
            category: Kategori.
            amount: Tutar.
            period: Donem.

        Returns:
            Kayit bilgisi.
        """
        try:
            bid = f"bg_{uuid4()!s:.8}"
            budget = {
                "budget_id": bid,
                "category": category,
                "amount": amount,
                "period": period,
                "timestamp": datetime.now(
                    timezone.utc
                ).isoformat(),
            }
            self._budgets.append(budget)
            self._stats["budgets_set"] += 1

            return {
                "budget_id": bid,
                "category": category,
                "amount": amount,
                "set": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "set": False,
                "error": str(e),
            }

    def record_actual(
        self,
        category: str = "",
        amount: float = 0.0,
        period: str = "",
        description: str = "",
    ) -> dict[str, Any]:
        """Gercek harcama kaydeder.

        Args:
            category: Kategori.
            amount: Tutar.
            period: Donem.
            description: Aciklama.

        Returns:
            Kayit bilgisi.
        """
        try:
            aid = f"at_{uuid4()!s:.8}"
            actual = {
                "actual_id": aid,
                "category": category,
                "amount": amount,
                "period": period,
                "description": description,
                "timestamp": datetime.now(
                    timezone.utc
                ).isoformat(),
            }
            self._actuals.append(actual)
            self._stats[
                "actuals_recorded"
            ] += 1

            return {
                "actual_id": aid,
                "category": category,
                "amount": amount,
                "recorded": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "recorded": False,
                "error": str(e),
            }

    def get_variance_analysis(
        self,
        period: str = "",
    ) -> dict[str, Any]:
        """Sapma analizi yapar.

        Args:
            period: Donem filtresi.

        Returns:
            Sapma bilgisi.
        """
        try:
            budget_map: dict[
                str, float
            ] = {}
            for b in self._budgets:
                if period and b.get(
                    "period"
                ) != period:
                    continue
                cat = b["category"]
                budget_map[cat] = (
                    budget_map.get(cat, 0.0)
                    + b["amount"]
                )

            actual_map: dict[
                str, float
            ] = {}
            for a in self._actuals:
                if period and a.get(
                    "period"
                ) != period:
                    continue
                cat = a["category"]
                actual_map[cat] = (
                    actual_map.get(cat, 0.0)
                    + a["amount"]
                )

            all_cats = set(
                list(budget_map.keys())
                + list(actual_map.keys())
            )

            variances = []
            for cat in sorted(all_cats):
                budgeted = budget_map.get(
                    cat, 0.0
                )
                actual = actual_map.get(
                    cat, 0.0
                )
                variance = actual - budgeted
                pct = (
                    (
                        variance
                        / budgeted
                        * 100
                    )
                    if budgeted > 0
                    else 0.0
                )

                status = (
                    "over_budget"
                    if variance > 0
                    else "under_budget"
                    if variance < 0
                    else "on_budget"
                )

                variances.append({
                    "category": cat,
                    "budgeted": round(
                        budgeted, 2
                    ),
                    "actual": round(
                        actual, 2
                    ),
                    "variance": round(
                        variance, 2
                    ),
                    "variance_pct": round(
                        pct, 1
                    ),
                    "status": status,
                })

            return {
                "variances": variances,
                "category_count": len(
                    variances
                ),
                "period": period,
                "analyzed": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "analyzed": False,
                "error": str(e),
            }

    def check_overruns(
        self,
        threshold_pct: float = 10.0,
    ) -> dict[str, Any]:
        """Asim kontrolu yapar.

        Args:
            threshold_pct: Esik yuzdesi.

        Returns:
            Asim bilgisi.
        """
        try:
            analysis = (
                self.get_variance_analysis()
            )
            variances = analysis.get(
                "variances", []
            )

            overruns = [
                v
                for v in variances
                if v["variance_pct"]
                > threshold_pct
            ]

            self._stats[
                "alerts_raised"
            ] += len(overruns)

            return {
                "overruns": overruns,
                "overrun_count": len(
                    overruns
                ),
                "threshold_pct": (
                    threshold_pct
                ),
                "checked": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "checked": False,
                "error": str(e),
            }

    def get_utilization(
        self,
        period: str = "",
    ) -> dict[str, Any]:
        """Butce kullanim oranini getirir.

        Args:
            period: Donem filtresi.

        Returns:
            Kullanim bilgisi.
        """
        try:
            analysis = (
                self.get_variance_analysis(
                    period=period
                )
            )
            variances = analysis.get(
                "variances", []
            )

            total_budget = sum(
                v["budgeted"]
                for v in variances
            )
            total_actual = sum(
                v["actual"]
                for v in variances
            )

            utilization = (
                (
                    total_actual
                    / total_budget
                    * 100
                )
                if total_budget > 0
                else 0.0
            )

            return {
                "total_budget": round(
                    total_budget, 2
                ),
                "total_actual": round(
                    total_actual, 2
                ),
                "utilization_pct": round(
                    utilization, 1
                ),
                "remaining": round(
                    total_budget
                    - total_actual,
                    2,
                ),
                "period": period,
                "retrieved": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "retrieved": False,
                "error": str(e),
            }

    def drill_down(
        self,
        category: str = "",
        period: str = "",
    ) -> dict[str, Any]:
        """Detaya iner.

        Args:
            category: Kategori.
            period: Donem.

        Returns:
            Detay bilgisi.
        """
        try:
            budgets = [
                b
                for b in self._budgets
                if b["category"] == category
                and (
                    not period
                    or b.get("period")
                    == period
                )
            ]
            actuals = [
                a
                for a in self._actuals
                if a["category"] == category
                and (
                    not period
                    or a.get("period")
                    == period
                )
            ]

            total_budget = sum(
                b["amount"] for b in budgets
            )
            total_actual = sum(
                a["amount"] for a in actuals
            )

            return {
                "category": category,
                "period": period,
                "total_budget": round(
                    total_budget, 2
                ),
                "total_actual": round(
                    total_actual, 2
                ),
                "variance": round(
                    total_actual
                    - total_budget,
                    2,
                ),
                "line_items": actuals,
                "line_count": len(actuals),
                "retrieved": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "retrieved": False,
                "error": str(e),
            }
