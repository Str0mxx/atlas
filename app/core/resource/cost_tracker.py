"""ATLAS Maliyet Takipcisi modulu.

Kaynak maliyeti hesaplama, butce takibi,
maliyet dagitimi, fatura uyarilari
ve optimizasyon onerileri.
"""

import logging
from datetime import datetime, timezone
from typing import Any

from app.models.resource import CostCategory, CostRecord

logger = logging.getLogger(__name__)


class CostTracker:
    """Maliyet takipcisi.

    Kaynak maliyetlerini izler, butceyi
    kontrol eder ve uyari uretir.

    Attributes:
        _records: Maliyet kayitlari.
        _budgets: Butce limitleri.
        _alerts: Fatura uyarilari.
    """

    def __init__(
        self,
        monthly_budget: float = 0.0,
    ) -> None:
        """Maliyet takipcisini baslatir.

        Args:
            monthly_budget: Aylik butce.
        """
        self._records: list[CostRecord] = []
        self._budgets: dict[str, float] = {}
        self._alerts: list[dict[str, Any]] = []
        self._monthly_budget = max(0.0, monthly_budget)

        if monthly_budget > 0:
            self._budgets["total"] = monthly_budget

        logger.info("CostTracker baslatildi")

    def record_cost(
        self,
        category: CostCategory,
        amount: float,
        resource: str = "",
        currency: str = "USD",
    ) -> CostRecord:
        """Maliyet kaydeder.

        Args:
            category: Kategori.
            amount: Miktar.
            resource: Kaynak.
            currency: Para birimi.

        Returns:
            Maliyet kaydi.
        """
        record = CostRecord(
            category=category,
            amount=max(0.0, amount),
            resource=resource,
            currency=currency,
        )
        self._records.append(record)

        # Butce kontrolu
        self._check_budget_alerts()
        return record

    def set_budget(
        self,
        category: str,
        amount: float,
    ) -> None:
        """Butce limiti ayarlar.

        Args:
            category: Kategori.
            amount: Limit miktari.
        """
        self._budgets[category] = max(0.0, amount)

    def get_total_cost(
        self,
        category: CostCategory | None = None,
    ) -> float:
        """Toplam maliyeti hesaplar.

        Args:
            category: Kategori filtresi.

        Returns:
            Toplam maliyet.
        """
        records = self._records
        if category:
            records = [
                r for r in records
                if r.category == category
            ]
        return sum(r.amount for r in records)

    def get_cost_breakdown(self) -> dict[str, float]:
        """Maliyet dagilimini getirir.

        Returns:
            Kategori bazli maliyet.
        """
        breakdown: dict[str, float] = {}
        for record in self._records:
            cat = record.category.value
            breakdown[cat] = breakdown.get(cat, 0.0) + record.amount
        return breakdown

    def get_cost_by_resource(self) -> dict[str, float]:
        """Kaynak bazli maliyeti getirir.

        Returns:
            Kaynak bazli maliyet.
        """
        by_resource: dict[str, float] = {}
        for record in self._records:
            res = record.resource or "unspecified"
            by_resource[res] = (
                by_resource.get(res, 0.0) + record.amount
            )
        return by_resource

    def check_budget(
        self,
        category: str = "total",
    ) -> dict[str, Any]:
        """Butce durumunu kontrol eder.

        Args:
            category: Kategori.

        Returns:
            Butce durumu.
        """
        budget = self._budgets.get(category)
        if budget is None:
            return {"has_budget": False}

        if category == "total":
            spent = self.get_total_cost()
        else:
            try:
                cat = CostCategory(category)
                spent = self.get_total_cost(cat)
            except ValueError:
                spent = 0.0

        remaining = max(0.0, budget - spent)
        ratio = spent / budget if budget > 0 else 0.0

        return {
            "has_budget": True,
            "budget": budget,
            "spent": spent,
            "remaining": remaining,
            "usage_ratio": ratio,
            "over_budget": spent > budget,
        }

    def get_optimization_suggestions(
        self,
    ) -> list[dict[str, Any]]:
        """Optimizasyon onerileri uretir.

        Returns:
            Oneri listesi.
        """
        suggestions: list[dict[str, Any]] = []
        breakdown = self.get_cost_breakdown()
        total = sum(breakdown.values())

        if total == 0:
            return suggestions

        for cat, amount in breakdown.items():
            ratio = amount / total
            if ratio > 0.5:
                suggestions.append({
                    "category": cat,
                    "amount": amount,
                    "share": ratio,
                    "suggestion": (
                        f"{cat} maliyetleri toplamin "
                        f"%{ratio*100:.0f}'ini olusturuyor, "
                        f"optimizasyon oneriliyor"
                    ),
                })

        return suggestions

    def _check_budget_alerts(self) -> None:
        """Butce uyarilarini kontrol eder."""
        for category, budget in self._budgets.items():
            if budget <= 0:
                continue

            if category == "total":
                spent = self.get_total_cost()
            else:
                try:
                    cat = CostCategory(category)
                    spent = self.get_total_cost(cat)
                except ValueError:
                    continue

            ratio = spent / budget
            if ratio >= 1.0:
                self._alerts.append({
                    "category": category,
                    "type": "over_budget",
                    "spent": spent,
                    "budget": budget,
                    "timestamp": datetime.now(
                        timezone.utc,
                    ).isoformat(),
                })
            elif ratio >= 0.8:
                self._alerts.append({
                    "category": category,
                    "type": "approaching_limit",
                    "spent": spent,
                    "budget": budget,
                    "ratio": ratio,
                    "timestamp": datetime.now(
                        timezone.utc,
                    ).isoformat(),
                })

    @property
    def record_count(self) -> int:
        """Kayit sayisi."""
        return len(self._records)

    @property
    def alert_count(self) -> int:
        """Uyari sayisi."""
        return len(self._alerts)

    @property
    def budget_count(self) -> int:
        """Butce sayisi."""
        return len(self._budgets)
