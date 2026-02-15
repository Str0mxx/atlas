"""ATLAS Butce Yoneticisi modulu.

Butce tahsisi, harcama limitleri,
gorev butceleri, donem butceleri, uyari esikleri.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class BudgetManager:
    """Butce yoneticisi.

    Butce tanimlarini ve harcamalari yonetir.

    Attributes:
        _budgets: Butce kayitlari.
        _spending: Harcama kayitlari.
    """

    def __init__(
        self,
        default_daily_limit: float = 100.0,
    ) -> None:
        """Butce yoneticisini baslatir.

        Args:
            default_daily_limit: Varsayilan gunluk limit.
        """
        self._budgets: dict[
            str, dict[str, Any]
        ] = {}
        self._spending: dict[
            str, float
        ] = {}
        self._alerts: list[
            dict[str, Any]
        ] = []
        self._default_daily = default_daily_limit
        self._stats = {
            "created": 0,
            "alerts_triggered": 0,
        }

        logger.info(
            "BudgetManager baslatildi",
        )

    def create_budget(
        self,
        budget_id: str,
        name: str,
        limit: float,
        period: str = "daily",
        alert_threshold: float = 0.8,
    ) -> dict[str, Any]:
        """Butce olusturur.

        Args:
            budget_id: Butce ID.
            name: Butce adi.
            limit: Limit.
            period: Donem.
            alert_threshold: Uyari esigi (oran).

        Returns:
            Butce bilgisi.
        """
        self._budgets[budget_id] = {
            "budget_id": budget_id,
            "name": name,
            "limit": limit,
            "period": period,
            "alert_threshold": alert_threshold,
            "spent": 0.0,
            "status": "active",
            "created_at": time.time(),
        }
        self._spending[budget_id] = 0.0
        self._stats["created"] += 1

        return {
            "budget_id": budget_id,
            "limit": limit,
            "created": True,
        }

    def allocate(
        self,
        budget_id: str,
        amount: float,
        description: str = "",
    ) -> dict[str, Any]:
        """Butceden harcar.

        Args:
            budget_id: Butce ID.
            amount: Miktar.
            description: Aciklama.

        Returns:
            Harcama bilgisi.
        """
        budget = self._budgets.get(budget_id)
        if not budget:
            return {"error": "budget_not_found"}

        budget["spent"] += amount
        self._spending[budget_id] += amount

        remaining = (
            budget["limit"] - budget["spent"]
        )
        usage_pct = (
            budget["spent"] / budget["limit"]
            if budget["limit"] > 0
            else 1.0
        )

        # Uyari kontrolu
        alert = None
        if usage_pct >= budget["alert_threshold"]:
            alert = self._trigger_alert(
                budget_id, usage_pct,
            )

        # Limit asimi
        exceeded = budget["spent"] > budget["limit"]
        if exceeded:
            budget["status"] = "exceeded"

        return {
            "budget_id": budget_id,
            "amount": amount,
            "spent": round(budget["spent"], 6),
            "remaining": round(
                max(remaining, 0), 6,
            ),
            "usage_pct": round(usage_pct, 4),
            "exceeded": exceeded,
            "alert": alert,
        }

    def check_budget(
        self,
        budget_id: str,
        amount: float = 0.0,
    ) -> dict[str, Any]:
        """Butce kontrol eder.

        Args:
            budget_id: Butce ID.
            amount: Planlanan harcama.

        Returns:
            Kontrol sonucu.
        """
        budget = self._budgets.get(budget_id)
        if not budget:
            return {"error": "budget_not_found"}

        remaining = (
            budget["limit"] - budget["spent"]
        )
        can_afford = remaining >= amount
        usage_pct = (
            budget["spent"] / budget["limit"]
            if budget["limit"] > 0
            else 1.0
        )

        return {
            "budget_id": budget_id,
            "limit": budget["limit"],
            "spent": round(budget["spent"], 6),
            "remaining": round(
                max(remaining, 0), 6,
            ),
            "usage_pct": round(usage_pct, 4),
            "can_afford": can_afford,
            "status": budget["status"],
        }

    def get_budget(
        self,
        budget_id: str,
    ) -> dict[str, Any] | None:
        """Butce getirir.

        Args:
            budget_id: Butce ID.

        Returns:
            Butce verisi veya None.
        """
        budget = self._budgets.get(budget_id)
        if budget:
            return dict(budget)
        return None

    def reset_budget(
        self,
        budget_id: str,
    ) -> dict[str, Any]:
        """Butceyi sifirlar.

        Args:
            budget_id: Butce ID.

        Returns:
            Sifirlama bilgisi.
        """
        budget = self._budgets.get(budget_id)
        if not budget:
            return {"error": "budget_not_found"}

        budget["spent"] = 0.0
        budget["status"] = "active"
        self._spending[budget_id] = 0.0

        return {
            "budget_id": budget_id,
            "reset": True,
        }

    def update_limit(
        self,
        budget_id: str,
        new_limit: float,
    ) -> dict[str, Any]:
        """Butce limitini gunceller.

        Args:
            budget_id: Butce ID.
            new_limit: Yeni limit.

        Returns:
            Guncelleme bilgisi.
        """
        budget = self._budgets.get(budget_id)
        if not budget:
            return {"error": "budget_not_found"}

        old_limit = budget["limit"]
        budget["limit"] = new_limit

        if budget["spent"] <= new_limit:
            budget["status"] = "active"

        return {
            "budget_id": budget_id,
            "old_limit": old_limit,
            "new_limit": new_limit,
            "updated": True,
        }

    def list_budgets(
        self,
        status: str | None = None,
    ) -> list[dict[str, Any]]:
        """Butceleri listeler.

        Args:
            status: Durum filtresi.

        Returns:
            Butce listesi.
        """
        budgets = list(self._budgets.values())
        if status:
            budgets = [
                b for b in budgets
                if b.get("status") == status
            ]
        return budgets

    def get_total_spending(
        self,
    ) -> dict[str, Any]:
        """Toplam harcama bilgisi.

        Returns:
            Harcama ozeti.
        """
        total = sum(self._spending.values())
        total_limit = sum(
            b["limit"]
            for b in self._budgets.values()
        )

        return {
            "total_spent": round(total, 6),
            "total_limit": round(total_limit, 6),
            "budget_count": len(self._budgets),
            "exceeded_count": sum(
                1 for b in self._budgets.values()
                if b["status"] == "exceeded"
            ),
        }

    def _trigger_alert(
        self,
        budget_id: str,
        usage_pct: float,
    ) -> dict[str, Any]:
        """Butce uyarisi tetikler.

        Args:
            budget_id: Butce ID.
            usage_pct: Kullanim orani.

        Returns:
            Uyari bilgisi.
        """
        severity = (
            "critical" if usage_pct >= 1.0
            else "warning"
        )

        alert = {
            "budget_id": budget_id,
            "usage_pct": round(usage_pct, 4),
            "severity": severity,
            "timestamp": time.time(),
        }

        self._alerts.append(alert)
        self._stats["alerts_triggered"] += 1

        return alert

    @property
    def budget_count(self) -> int:
        """Butce sayisi."""
        return len(self._budgets)

    @property
    def alert_count(self) -> int:
        """Uyari sayisi."""
        return len(self._alerts)
