"""ATLAS Gelir Takipçisi modülü.

Gelir kaydı, kaynak sınıflandırma,
tekrarlayan gelir, fatura takibi,
büyüme analizi.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class IncomeTracker:
    """Gelir takipçisi.

    Gelir kaynaklarını takip eder ve analiz eder.

    Attributes:
        _incomes: Gelir kayıtları.
        _sources: Kaynak sınıflandırmaları.
    """

    def __init__(
        self,
        currency: str = "TRY",
    ) -> None:
        """Takipçiyi başlatır.

        Args:
            currency: Varsayılan para birimi.
        """
        self._incomes: list[
            dict[str, Any]
        ] = []
        self._sources: dict[
            str, list[dict[str, Any]]
        ] = {}
        self._recurring: list[
            dict[str, Any]
        ] = []
        self._currency = currency
        self._counter = 0
        self._stats = {
            "total_income": 0.0,
            "transactions": 0,
            "sources": 0,
        }

        logger.info(
            "IncomeTracker baslatildi",
        )

    def record_income(
        self,
        amount: float,
        source: str,
        category: str = "general",
        description: str = "",
        recurring: bool = False,
    ) -> dict[str, Any]:
        """Gelir kaydeder.

        Args:
            amount: Tutar.
            source: Kaynak.
            category: Kategori.
            description: Açıklama.
            recurring: Tekrarlayan mı.

        Returns:
            Kayıt bilgisi.
        """
        self._counter += 1
        iid = f"inc_{self._counter}"

        record = {
            "income_id": iid,
            "amount": amount,
            "source": source,
            "category": category,
            "description": description,
            "recurring": recurring,
            "currency": self._currency,
            "timestamp": time.time(),
        }
        self._incomes.append(record)

        # Kaynak sınıflandırma
        if source not in self._sources:
            self._sources[source] = []
            self._stats["sources"] += 1
        self._sources[source].append(record)

        # Tekrarlayan gelir
        if recurring:
            self._recurring.append(record)

        self._stats["total_income"] += amount
        self._stats["transactions"] += 1

        return {
            "income_id": iid,
            "amount": amount,
            "source": source,
            "recorded": True,
        }

    def get_by_source(
        self,
        source: str,
    ) -> dict[str, Any]:
        """Kaynağa göre getirir.

        Args:
            source: Kaynak adı.

        Returns:
            Kaynak bilgisi.
        """
        records = self._sources.get(
            source, [],
        )
        total = sum(
            r["amount"] for r in records
        )
        return {
            "source": source,
            "total": round(total, 2),
            "count": len(records),
            "records": records[-10:],
        }

    def get_by_category(
        self,
        category: str,
    ) -> dict[str, Any]:
        """Kategoriye göre getirir.

        Args:
            category: Kategori.

        Returns:
            Kategori bilgisi.
        """
        filtered = [
            r for r in self._incomes
            if r["category"] == category
        ]
        total = sum(
            r["amount"] for r in filtered
        )
        return {
            "category": category,
            "total": round(total, 2),
            "count": len(filtered),
        }

    def get_recurring(
        self,
    ) -> dict[str, Any]:
        """Tekrarlayan gelirleri getirir.

        Returns:
            Tekrarlayan gelir bilgisi.
        """
        total = sum(
            r["amount"]
            for r in self._recurring
        )
        return {
            "recurring_incomes": len(
                self._recurring,
            ),
            "monthly_total": round(total, 2),
            "sources": list({
                r["source"]
                for r in self._recurring
            }),
        }

    def analyze_growth(
        self,
    ) -> dict[str, Any]:
        """Büyüme analizi yapar.

        Returns:
            Büyüme bilgisi.
        """
        if len(self._incomes) < 2:
            return {
                "growth_rate": 0.0,
                "trend": "insufficient_data",
            }

        mid = len(self._incomes) // 2
        first_half = sum(
            r["amount"]
            for r in self._incomes[:mid]
        )
        second_half = sum(
            r["amount"]
            for r in self._incomes[mid:]
        )

        if first_half == 0:
            growth = (
                100.0 if second_half > 0
                else 0.0
            )
        else:
            growth = round(
                (second_half - first_half)
                / first_half * 100,
                2,
            )

        trend = (
            "growing" if growth > 5
            else "declining" if growth < -5
            else "stable"
        )

        return {
            "growth_rate": growth,
            "first_half_total": round(
                first_half, 2,
            ),
            "second_half_total": round(
                second_half, 2,
            ),
            "trend": trend,
        }

    def get_source_breakdown(
        self,
    ) -> dict[str, Any]:
        """Kaynak dağılımını döndürür."""
        breakdown = {}
        total = self._stats["total_income"]
        for source, records in (
            self._sources.items()
        ):
            src_total = sum(
                r["amount"] for r in records
            )
            pct = (
                round(src_total / total * 100, 1)
                if total > 0 else 0.0
            )
            breakdown[source] = {
                "total": round(src_total, 2),
                "percentage": pct,
                "count": len(records),
            }
        return {
            "breakdown": breakdown,
            "total_income": round(total, 2),
            "source_count": len(breakdown),
        }

    @property
    def total_income(self) -> float:
        """Toplam gelir."""
        return round(
            self._stats["total_income"], 2,
        )

    @property
    def income_count(self) -> int:
        """Gelir sayısı."""
        return self._stats["transactions"]

    @property
    def source_count(self) -> int:
        """Kaynak sayısı."""
        return self._stats["sources"]
