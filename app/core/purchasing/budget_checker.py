"""ATLAS Bütçe Kontrolcüsü modülü.

Bütçe limitleri, harcama takibi,
onay eşikleri, tahmin etkisi,
uyarı üretimi.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class PurchaseBudgetChecker:
    """Satın alma bütçe kontrolcüsü.

    Satın alma bütçesini kontrol eder.

    Attributes:
        _budgets: Bütçe kayıtları.
        _spending: Harcama kayıtları.
    """

    def __init__(self) -> None:
        """Kontrolcüyü başlatır."""
        self._budgets: dict[
            str, dict[str, Any]
        ] = {}
        self._spending: list[
            dict[str, Any]
        ] = []
        self._alerts: list[
            dict[str, Any]
        ] = []
        self._counter = 0
        self._stats = {
            "checks_done": 0,
            "alerts_generated": 0,
        }

        logger.info(
            "PurchaseBudgetChecker "
            "baslatildi",
        )

    def set_limit(
        self,
        category: str,
        limit_amount: float,
        period: str = "monthly",
    ) -> dict[str, Any]:
        """Bütçe limiti belirler.

        Args:
            category: Kategori.
            limit_amount: Limit tutarı.
            period: Dönem.

        Returns:
            Limit bilgisi.
        """
        self._counter += 1
        bid = f"bud_{self._counter}"

        self._budgets[category] = {
            "budget_id": bid,
            "category": category,
            "limit": limit_amount,
            "spent": 0.0,
            "period": period,
            "timestamp": time.time(),
        }

        return {
            "budget_id": bid,
            "category": category,
            "limit": limit_amount,
            "period": period,
            "set": True,
        }

    def record_spending(
        self,
        category: str,
        amount: float,
        description: str = "",
    ) -> dict[str, Any]:
        """Harcama kaydeder.

        Args:
            category: Kategori.
            amount: Tutar.
            description: Açıklama.

        Returns:
            Kayıt bilgisi.
        """
        entry = {
            "category": category,
            "amount": amount,
            "description": description,
            "timestamp": time.time(),
        }
        self._spending.append(entry)

        if category in self._budgets:
            self._budgets[category][
                "spent"
            ] += amount

        return {
            "category": category,
            "amount": amount,
            "recorded": True,
        }

    def check_budget(
        self,
        category: str,
        proposed_amount: float = 0.0,
    ) -> dict[str, Any]:
        """Bütçe kontrol eder.

        Args:
            category: Kategori.
            proposed_amount: Teklif tutarı.

        Returns:
            Kontrol bilgisi.
        """
        if category not in self._budgets:
            return {
                "category": category,
                "status": "no_budget",
                "checked": False,
            }

        budget = self._budgets[category]
        limit_amt = budget["limit"]
        spent = budget["spent"]
        remaining = limit_amt - spent
        projected = spent + proposed_amount

        usage_pct = round(
            projected
            / max(limit_amt, 0.01) * 100,
            1,
        )

        status = (
            "within" if usage_pct <= 80
            else "warning" if usage_pct <= 100
            else "exceeded"
        )

        self._stats["checks_done"] += 1

        return {
            "category": category,
            "limit": limit_amt,
            "spent": spent,
            "remaining": round(
                remaining, 2,
            ),
            "proposed": proposed_amount,
            "projected": round(
                projected, 2,
            ),
            "usage_pct": usage_pct,
            "status": status,
            "approved": status != "exceeded",
            "checked": True,
        }

    def get_approval_threshold(
        self,
        amount: float,
    ) -> dict[str, Any]:
        """Onay eşiği döndürür.

        Args:
            amount: Tutar.

        Returns:
            Eşik bilgisi.
        """
        if amount < 100:
            level = "auto"
        elif amount < 1000:
            level = "manager"
        elif amount < 5000:
            level = "director"
        else:
            level = "executive"

        return {
            "amount": amount,
            "approval_level": level,
            "auto_approved": level == "auto",
        }

    def forecast_impact(
        self,
        category: str,
        planned_purchases: list[float]
        | None = None,
    ) -> dict[str, Any]:
        """Tahmin etkisi hesaplar.

        Args:
            category: Kategori.
            planned_purchases: Planlananlar.

        Returns:
            Tahmin bilgisi.
        """
        planned_purchases = (
            planned_purchases or []
        )

        if category not in self._budgets:
            return {
                "category": category,
                "forecasted": False,
            }

        budget = self._budgets[category]
        current_spent = budget["spent"]
        planned_total = sum(
            planned_purchases,
        )
        projected = (
            current_spent + planned_total
        )
        limit_amt = budget["limit"]

        usage_pct = round(
            projected
            / max(limit_amt, 0.01) * 100,
            1,
        )

        status = (
            "safe" if usage_pct <= 80
            else "tight" if usage_pct <= 100
            else "over_budget"
        )

        return {
            "category": category,
            "current_spent": current_spent,
            "planned_total": round(
                planned_total, 2,
            ),
            "projected": round(
                projected, 2,
            ),
            "limit": limit_amt,
            "usage_pct": usage_pct,
            "status": status,
            "forecasted": True,
        }

    def generate_alert(
        self,
        category: str,
    ) -> dict[str, Any]:
        """Uyarı üretir.

        Args:
            category: Kategori.

        Returns:
            Uyarı bilgisi.
        """
        check = self.check_budget(category)

        if not check.get("checked"):
            return {
                "category": category,
                "alert": False,
            }

        alerts = []
        usage = check["usage_pct"]

        if usage >= 100:
            alerts.append({
                "level": "critical",
                "message": (
                    f"Budget exceeded: "
                    f"{usage}%"
                ),
            })
        elif usage >= 80:
            alerts.append({
                "level": "warning",
                "message": (
                    f"Budget at {usage}%"
                ),
            })

        self._alerts.extend(alerts)
        self._stats[
            "alerts_generated"
        ] += len(alerts)

        return {
            "category": category,
            "alerts": alerts,
            "alert_count": len(alerts),
            "alert": len(alerts) > 0,
        }

    @property
    def check_count(self) -> int:
        """Kontrol sayısı."""
        return self._stats["checks_done"]

    @property
    def alert_count(self) -> int:
        """Uyarı sayısı."""
        return self._stats[
            "alerts_generated"
        ]
