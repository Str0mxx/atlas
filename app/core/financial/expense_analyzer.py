"""ATLAS Gider Analizcisi modülü.

Gider sınıflandırma, trend analizi,
anomali tespiti, bütçe karşılaştırma,
maliyet optimizasyonu.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class ExpenseAnalyzer:
    """Gider analizcisi.

    Giderleri sınıflandırır ve analiz eder.

    Attributes:
        _expenses: Gider kayıtları.
        _budgets: Bütçe limitleri.
    """

    def __init__(
        self,
        currency: str = "TRY",
    ) -> None:
        """Analizcisini başlatır.

        Args:
            currency: Varsayılan para birimi.
        """
        self._expenses: list[
            dict[str, Any]
        ] = []
        self._categories: dict[
            str, list[dict[str, Any]]
        ] = {}
        self._budgets: dict[str, float] = {}
        self._currency = currency
        self._counter = 0
        self._stats = {
            "total_expense": 0.0,
            "transactions": 0,
            "categories": 0,
            "anomalies_detected": 0,
        }

        logger.info(
            "ExpenseAnalyzer baslatildi",
        )

    def record_expense(
        self,
        amount: float,
        category: str,
        vendor: str = "",
        description: str = "",
    ) -> dict[str, Any]:
        """Gider kaydeder.

        Args:
            amount: Tutar.
            category: Kategori.
            vendor: Satıcı.
            description: Açıklama.

        Returns:
            Kayıt bilgisi.
        """
        self._counter += 1
        eid = f"exp_{self._counter}"

        record = {
            "expense_id": eid,
            "amount": amount,
            "category": category,
            "vendor": vendor,
            "description": description,
            "currency": self._currency,
            "timestamp": time.time(),
        }
        self._expenses.append(record)

        if category not in self._categories:
            self._categories[category] = []
            self._stats["categories"] += 1
        self._categories[category].append(
            record,
        )

        self._stats["total_expense"] += amount
        self._stats["transactions"] += 1

        return {
            "expense_id": eid,
            "amount": amount,
            "category": category,
            "recorded": True,
        }

    def set_budget(
        self,
        category: str,
        limit: float,
    ) -> dict[str, Any]:
        """Bütçe limiti ayarlar.

        Args:
            category: Kategori.
            limit: Limit.

        Returns:
            Ayar bilgisi.
        """
        self._budgets[category] = limit
        return {
            "category": category,
            "limit": limit,
            "set": True,
        }

    def analyze_trends(
        self,
    ) -> dict[str, Any]:
        """Trend analizi yapar.

        Returns:
            Trend bilgisi.
        """
        if len(self._expenses) < 2:
            return {
                "trend": "insufficient_data",
                "categories": {},
            }

        cat_trends: dict[str, str] = {}
        for cat, records in (
            self._categories.items()
        ):
            if len(records) < 2:
                cat_trends[cat] = "stable"
                continue
            mid = len(records) // 2
            first = sum(
                r["amount"]
                for r in records[:mid]
            )
            second = sum(
                r["amount"]
                for r in records[mid:]
            )
            if second > first * 1.1:
                cat_trends[cat] = "increasing"
            elif second < first * 0.9:
                cat_trends[cat] = "decreasing"
            else:
                cat_trends[cat] = "stable"

        return {
            "trend": "analyzed",
            "categories": cat_trends,
            "total_categories": len(
                cat_trends,
            ),
        }

    def detect_anomalies(
        self,
        threshold: float = 2.0,
    ) -> dict[str, Any]:
        """Anomali tespit eder.

        Args:
            threshold: Eşik çarpanı.

        Returns:
            Anomali bilgisi.
        """
        anomalies = []

        for cat, records in (
            self._categories.items()
        ):
            if len(records) < 3:
                continue
            amounts = [
                r["amount"] for r in records
            ]
            avg = sum(amounts) / len(amounts)

            for rec in records:
                if rec["amount"] > (
                    avg * threshold
                ):
                    anomalies.append({
                        "expense_id": rec[
                            "expense_id"
                        ],
                        "category": cat,
                        "amount": rec["amount"],
                        "average": round(
                            avg, 2,
                        ),
                        "ratio": round(
                            rec["amount"] / avg,
                            2,
                        ),
                    })

        self._stats[
            "anomalies_detected"
        ] = len(anomalies)

        return {
            "anomalies": anomalies,
            "count": len(anomalies),
        }

    def compare_budget(
        self,
    ) -> dict[str, Any]:
        """Bütçe karşılaştırması yapar.

        Returns:
            Karşılaştırma bilgisi.
        """
        comparisons = {}
        over_budget = []

        for cat, limit in (
            self._budgets.items()
        ):
            records = self._categories.get(
                cat, [],
            )
            spent = sum(
                r["amount"] for r in records
            )
            remaining = limit - spent
            usage = (
                round(spent / limit * 100, 1)
                if limit > 0 else 0.0
            )

            comp = {
                "budget": limit,
                "spent": round(spent, 2),
                "remaining": round(
                    remaining, 2,
                ),
                "usage_percent": usage,
                "over_budget": spent > limit,
            }
            comparisons[cat] = comp

            if spent > limit:
                over_budget.append(cat)

        return {
            "comparisons": comparisons,
            "over_budget": over_budget,
            "total_categories": len(
                comparisons,
            ),
        }

    def suggest_optimizations(
        self,
    ) -> dict[str, Any]:
        """Maliyet optimizasyonu önerir.

        Returns:
            Öneri bilgisi.
        """
        suggestions = []

        # Bütçe aşımı
        budget_comp = self.compare_budget()
        for cat in budget_comp["over_budget"]:
            comp = budget_comp[
                "comparisons"
            ][cat]
            suggestions.append({
                "type": "over_budget",
                "category": cat,
                "overspend": round(
                    comp["spent"]
                    - comp["budget"], 2,
                ),
                "suggestion": (
                    f"Reduce {cat} spending "
                    f"by {comp['spent'] - comp['budget']:.0f} "
                    f"{self._currency}"
                ),
            })

        # Yüksek harcama kategorileri
        total = self._stats["total_expense"]
        if total > 0:
            for cat, records in (
                self._categories.items()
            ):
                cat_total = sum(
                    r["amount"]
                    for r in records
                )
                pct = cat_total / total * 100
                if pct > 40:
                    suggestions.append({
                        "type": "high_concentration",
                        "category": cat,
                        "percentage": round(
                            pct, 1,
                        ),
                        "suggestion": (
                            f"{cat} is {pct:.0f}% "
                            f"of total spending"
                        ),
                    })

        return {
            "suggestions": suggestions,
            "count": len(suggestions),
        }

    def get_category_breakdown(
        self,
    ) -> dict[str, Any]:
        """Kategori dağılımını döndürür."""
        breakdown = {}
        total = self._stats["total_expense"]
        for cat, records in (
            self._categories.items()
        ):
            cat_total = sum(
                r["amount"] for r in records
            )
            pct = (
                round(
                    cat_total / total * 100, 1,
                )
                if total > 0 else 0.0
            )
            breakdown[cat] = {
                "total": round(cat_total, 2),
                "percentage": pct,
                "count": len(records),
            }
        return {
            "breakdown": breakdown,
            "total_expense": round(total, 2),
        }

    @property
    def total_expense(self) -> float:
        """Toplam gider."""
        return round(
            self._stats["total_expense"], 2,
        )

    @property
    def expense_count(self) -> int:
        """Gider sayısı."""
        return self._stats["transactions"]

    @property
    def category_count(self) -> int:
        """Kategori sayısı."""
        return self._stats["categories"]
