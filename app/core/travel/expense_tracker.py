"""
Seyahat harcama takip modülü.

Harcama kayıt, döviz çevirme, bütçe takibi,
fiş yönetimi, rapor üretimi.
"""

import logging
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)


class TravelExpenseTracker:
    """Seyahat harcama takipçisi.

    Attributes:
        _expenses: Harcama kayıtları.
        _stats: İstatistikler.
    """

    def __init__(self) -> None:
        """Takipçiyi başlatır."""
        self._expenses: list[dict] = []
        self._stats: dict[str, int] = {
            "expenses_logged": 0,
        }
        logger.info(
            "TravelExpenseTracker baslatildi"
        )

    @property
    def expense_count(self) -> int:
        """Harcama sayısı."""
        return len(self._expenses)

    def log_expense(
        self,
        category: str = "other",
        amount: float = 0.0,
        currency: str = "USD",
        description: str = "",
    ) -> dict[str, Any]:
        """Harcama kaydı ekler.

        Args:
            category: Kategori.
            amount: Tutar.
            currency: Para birimi.
            description: Açıklama.

        Returns:
            Kayıt bilgisi.
        """
        try:
            eid = f"exp_{uuid4()!s:.8}"

            record = {
                "expense_id": eid,
                "category": category,
                "amount": amount,
                "currency": currency,
                "description": description,
            }
            self._expenses.append(record)
            self._stats["expenses_logged"] += 1

            return {
                "expense_id": eid,
                "category": category,
                "amount": amount,
                "currency": currency,
                "logged": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "logged": False,
                "error": str(e),
            }

    def convert_currency(
        self,
        amount: float = 0.0,
        from_currency: str = "USD",
        to_currency: str = "TRY",
    ) -> dict[str, Any]:
        """Döviz çevirimi yapar.

        Args:
            amount: Tutar.
            from_currency: Kaynak para birimi.
            to_currency: Hedef para birimi.

        Returns:
            Çevirim sonucu.
        """
        try:
            rates = {
                ("USD", "TRY"): 32.0,
                ("EUR", "TRY"): 35.0,
                ("GBP", "TRY"): 40.0,
                ("USD", "EUR"): 0.92,
                ("EUR", "USD"): 1.09,
                ("TRY", "USD"): 0.031,
                ("TRY", "EUR"): 0.029,
            }

            pair = (from_currency, to_currency)
            rate = rates.get(pair, 1.0)
            converted = round(amount * rate, 2)

            return {
                "original_amount": amount,
                "from_currency": from_currency,
                "to_currency": to_currency,
                "rate": rate,
                "converted_amount": converted,
                "converted": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "converted": False,
                "error": str(e),
            }

    def track_budget(
        self,
        total_budget: float = 0.0,
    ) -> dict[str, Any]:
        """Bütçe takibi yapar.

        Args:
            total_budget: Toplam bütçe.

        Returns:
            Bütçe durumu.
        """
        try:
            total_spent = sum(
                e["amount"]
                for e in self._expenses
            )
            remaining = total_budget - total_spent
            used_pct = round(
                total_spent / total_budget * 100,
                1,
            ) if total_budget > 0 else 0.0

            if used_pct > 100:
                status = "over_budget"
            elif used_pct >= 80:
                status = "near_limit"
            elif used_pct >= 50:
                status = "on_track"
            else:
                status = "under_budget"

            return {
                "total_budget": total_budget,
                "total_spent": round(
                    total_spent, 2
                ),
                "remaining": round(remaining, 2),
                "used_pct": used_pct,
                "status": status,
                "tracked": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "tracked": False,
                "error": str(e),
            }

    def manage_receipts(
        self,
        expense_id: str = "",
        receipt_name: str = "",
    ) -> dict[str, Any]:
        """Fiş yönetir.

        Args:
            expense_id: Harcama ID.
            receipt_name: Fiş adı.

        Returns:
            Fiş bilgisi.
        """
        try:
            exp = None
            for e in self._expenses:
                if e["expense_id"] == expense_id:
                    exp = e
                    break

            if not exp:
                return {
                    "managed": False,
                    "error": "expense_not_found",
                }

            rid = f"rct_{uuid4()!s:.8}"
            if "receipts" not in exp:
                exp["receipts"] = []
            exp["receipts"].append({
                "receipt_id": rid,
                "name": receipt_name,
            })

            return {
                "receipt_id": rid,
                "expense_id": expense_id,
                "receipt_name": receipt_name,
                "total_receipts": len(
                    exp["receipts"]
                ),
                "managed": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "managed": False,
                "error": str(e),
            }

    def generate_report(
        self,
    ) -> dict[str, Any]:
        """Harcama raporu üretir.

        Returns:
            Harcama raporu.
        """
        try:
            if not self._expenses:
                return {
                    "generated": True,
                    "total": 0.0,
                    "expense_count": 0,
                    "categories": {},
                }

            total = sum(
                e["amount"]
                for e in self._expenses
            )

            categories: dict[str, float] = {}
            for exp in self._expenses:
                cat = exp["category"]
                categories[cat] = (
                    categories.get(cat, 0.0)
                    + exp["amount"]
                )

            top_category = max(
                categories,
                key=categories.get,  # type: ignore[arg-type]
            ) if categories else "none"

            return {
                "total": round(total, 2),
                "expense_count": len(
                    self._expenses
                ),
                "categories": categories,
                "top_category": top_category,
                "generated": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "generated": False,
                "error": str(e),
            }
