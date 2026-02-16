"""ATLAS Vergi Tahmincisi modülü.

Vergi hesaplama, indirim takibi,
çeyreklik tahminler, uyumluluk kontrolü,
beyanname hatırlatmaları.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class TaxEstimator:
    """Vergi tahmincisi.

    Vergi yükümlülüklerini tahmin eder.

    Attributes:
        _income_records: Gelir kayıtları.
        _deductions: İndirim kayıtları.
    """

    DEFAULT_BRACKETS = [
        (110000, 0.15),
        (230000, 0.20),
        (580000, 0.27),
        (3000000, 0.35),
        (float("inf"), 0.40),
    ]

    def __init__(
        self,
        tax_rate: float = 0.20,
        vat_rate: float = 0.20,
    ) -> None:
        """Tahmincisini başlatır.

        Args:
            tax_rate: Varsayılan vergi oranı.
            vat_rate: KDV oranı.
        """
        self._income_records: list[
            dict[str, Any]
        ] = []
        self._deductions: list[
            dict[str, Any]
        ] = []
        self._quarterly: dict[
            int, dict[str, Any]
        ] = {}
        self._reminders: list[
            dict[str, Any]
        ] = []
        self._tax_rate = tax_rate
        self._vat_rate = vat_rate
        self._counter = 0
        self._stats = {
            "estimates_made": 0,
            "deductions_tracked": 0,
            "reminders_created": 0,
        }

        logger.info(
            "TaxEstimator baslatildi",
        )

    def record_taxable_income(
        self,
        amount: float,
        quarter: int = 1,
        category: str = "general",
    ) -> dict[str, Any]:
        """Vergiye tabi gelir kaydeder.

        Args:
            amount: Tutar.
            quarter: Çeyrek (1-4).
            category: Kategori.

        Returns:
            Kayıt bilgisi.
        """
        self._counter += 1
        rid = f"tax_{self._counter}"

        record = {
            "record_id": rid,
            "amount": amount,
            "quarter": quarter,
            "category": category,
            "timestamp": time.time(),
        }
        self._income_records.append(record)

        if quarter not in self._quarterly:
            self._quarterly[quarter] = {
                "income": 0.0,
                "deductions": 0.0,
            }
        self._quarterly[quarter][
            "income"
        ] += amount

        return {
            "record_id": rid,
            "amount": amount,
            "quarter": quarter,
            "recorded": True,
        }

    def add_deduction(
        self,
        amount: float,
        category: str,
        quarter: int = 1,
        description: str = "",
    ) -> dict[str, Any]:
        """İndirim ekler.

        Args:
            amount: Tutar.
            category: Kategori.
            quarter: Çeyrek.
            description: Açıklama.

        Returns:
            İndirim bilgisi.
        """
        self._counter += 1
        did = f"ded_{self._counter}"

        deduction = {
            "deduction_id": did,
            "amount": amount,
            "category": category,
            "quarter": quarter,
            "description": description,
            "timestamp": time.time(),
        }
        self._deductions.append(deduction)
        self._stats[
            "deductions_tracked"
        ] += 1

        if quarter not in self._quarterly:
            self._quarterly[quarter] = {
                "income": 0.0,
                "deductions": 0.0,
            }
        self._quarterly[quarter][
            "deductions"
        ] += amount

        return {
            "deduction_id": did,
            "amount": amount,
            "category": category,
            "recorded": True,
        }

    def estimate_tax(
        self,
        income: float | None = None,
        use_brackets: bool = False,
    ) -> dict[str, Any]:
        """Vergi tahmini yapar.

        Args:
            income: Gelir tutarı.
            use_brackets: Dilim kullan.

        Returns:
            Tahmin bilgisi.
        """
        if income is None:
            income = sum(
                r["amount"]
                for r in self._income_records
            )

        total_deductions = sum(
            d["amount"]
            for d in self._deductions
        )
        taxable = max(
            0, income - total_deductions,
        )

        if use_brackets:
            tax = self._calc_bracketed(taxable)
            effective_rate = round(
                tax / max(taxable, 0.01)
                * 100, 2,
            )
        else:
            tax = round(
                taxable * self._tax_rate, 2,
            )
            effective_rate = round(
                self._tax_rate * 100, 2,
            )

        self._stats["estimates_made"] += 1

        return {
            "gross_income": round(income, 2),
            "deductions": round(
                total_deductions, 2,
            ),
            "taxable_income": round(
                taxable, 2,
            ),
            "estimated_tax": round(tax, 2),
            "effective_rate": effective_rate,
        }

    def _calc_bracketed(
        self,
        taxable: float,
    ) -> float:
        """Dilimli vergi hesaplar."""
        tax = 0.0
        prev_limit = 0.0

        for limit, rate in (
            self.DEFAULT_BRACKETS
        ):
            if taxable <= prev_limit:
                break
            bracket_income = (
                min(taxable, limit)
                - prev_limit
            )
            tax += bracket_income * rate
            prev_limit = limit

        return round(tax, 2)

    def estimate_quarterly(
        self,
        quarter: int,
    ) -> dict[str, Any]:
        """Çeyreklik tahmin yapar.

        Args:
            quarter: Çeyrek (1-4).

        Returns:
            Çeyreklik tahmin bilgisi.
        """
        q_data = self._quarterly.get(
            quarter,
            {"income": 0.0, "deductions": 0.0},
        )

        taxable = max(
            0,
            q_data["income"]
            - q_data["deductions"],
        )
        tax = round(
            taxable * self._tax_rate, 2,
        )

        return {
            "quarter": quarter,
            "income": round(
                q_data["income"], 2,
            ),
            "deductions": round(
                q_data["deductions"], 2,
            ),
            "taxable": round(taxable, 2),
            "estimated_tax": tax,
        }

    def check_compliance(
        self,
    ) -> dict[str, Any]:
        """Uyumluluk kontrolü yapar.

        Returns:
            Uyumluluk bilgisi.
        """
        issues = []

        # Her çeyrekte gelir var mı
        for q in range(1, 5):
            if q in self._quarterly:
                q_data = self._quarterly[q]
                if (
                    q_data["income"] > 0
                    and q_data["deductions"]
                    > q_data["income"]
                ):
                    issues.append({
                        "quarter": q,
                        "issue": (
                            "deductions_exceed_income"
                        ),
                        "severity": "warning",
                    })

        # İndirim belgeleri
        uncat_deductions = [
            d for d in self._deductions
            if not d["category"]
        ]
        if uncat_deductions:
            issues.append({
                "issue": (
                    "uncategorized_deductions"
                ),
                "count": len(uncat_deductions),
                "severity": "info",
            })

        return {
            "compliant": len(issues) == 0,
            "issues": issues,
            "count": len(issues),
        }

    def create_reminder(
        self,
        filing_type: str,
        due_date: str,
        description: str = "",
    ) -> dict[str, Any]:
        """Beyanname hatırlatması oluşturur.

        Args:
            filing_type: Beyanname tipi.
            due_date: Son tarih.
            description: Açıklama.

        Returns:
            Hatırlatma bilgisi.
        """
        self._counter += 1
        rid = f"taxrem_{self._counter}"

        reminder = {
            "reminder_id": rid,
            "filing_type": filing_type,
            "due_date": due_date,
            "description": description,
            "completed": False,
            "created_at": time.time(),
        }
        self._reminders.append(reminder)
        self._stats[
            "reminders_created"
        ] += 1

        return {
            "reminder_id": rid,
            "filing_type": filing_type,
            "due_date": due_date,
            "created": True,
        }

    def get_deduction_summary(
        self,
    ) -> dict[str, Any]:
        """İndirim özetini döndürür."""
        by_category: dict[str, float] = {}
        for d in self._deductions:
            cat = d["category"] or "other"
            by_category[cat] = (
                by_category.get(cat, 0)
                + d["amount"]
            )

        total = sum(by_category.values())
        return {
            "by_category": by_category,
            "total": round(total, 2),
            "count": len(self._deductions),
        }

    @property
    def estimate_count(self) -> int:
        """Tahmin sayısı."""
        return self._stats[
            "estimates_made"
        ]

    @property
    def deduction_count(self) -> int:
        """İndirim sayısı."""
        return self._stats[
            "deductions_tracked"
        ]

    @property
    def total_income(self) -> float:
        """Toplam gelir."""
        return round(
            sum(
                r["amount"]
                for r in self._income_records
            ),
            2,
        )
