"""
Harcama kategorizasyon modülü.

Otomatik kategorizasyon, özel kategoriler,
mağaza eşleme, örüntü öğrenme ve
bölme işlemleri sağlar.
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)


class SpendingCategorizer:
    """Harcama kategorizasyoncusu.

    Harcamaları otomatik kategorize eder,
    mağaza eşleme ve örüntü öğrenme yapar.

    Attributes:
        _mappings: Mağaza-kategori eşlemeleri.
        _stats: İstatistikler.
    """

    def __init__(self) -> None:
        """Kategorizasyoncuyu başlatır."""
        self._mappings: dict[str, str] = {
            "migros": "food",
            "bim": "food",
            "shell": "transport",
            "bp": "transport",
            "netflix": "entertainment",
            "spotify": "entertainment",
            "vodafone": "utilities",
            "turkcell": "utilities",
        }
        self._custom: dict[str, str] = {}
        self._stats: dict[str, int] = {
            "categorized": 0,
        }
        logger.info(
            "SpendingCategorizer "
            "baslatildi"
        )

    @property
    def categorized_count(self) -> int:
        """Kategorize edilen sayı."""
        return self._stats["categorized"]

    def auto_categorize(
        self,
        merchant: str = "",
        amount: float = 0.0,
    ) -> dict[str, Any]:
        """Otomatik kategorizasyon yapar.

        Args:
            merchant: Mağaza adı.
            amount: Tutar.

        Returns:
            Kategorizasyon sonucu.
        """
        try:
            low = merchant.lower()
            category = "uncategorized"

            # Önce özel eşlemeler
            if low in self._custom:
                category = self._custom[low]
            # Sonra varsayılan eşlemeler
            elif low in self._mappings:
                category = (
                    self._mappings[low]
                )
            # Anahtar kelime tarama
            else:
                kw_map = {
                    "market": "food",
                    "restoran": "food",
                    "taksi": "transport",
                    "otopark": "transport",
                    "hastane": "healthcare",
                    "eczane": "healthcare",
                }
                for kw, cat in kw_map.items():
                    if kw in low:
                        category = cat
                        break

            confidence = (
                0.95
                if category
                != "uncategorized"
                else 0.0
            )

            self._stats["categorized"] += 1

            return {
                "merchant": merchant,
                "amount": amount,
                "category": category,
                "confidence": confidence,
                "categorized": True,
            }

        except Exception as e:
            logger.error(
                f"Kategorizasyon "
                f"hatasi: {e}"
            )
            return {
                "merchant": merchant,
                "amount": amount,
                "category": "uncategorized",
                "confidence": 0.0,
                "categorized": False,
                "error": str(e),
            }

    def add_custom_category(
        self,
        merchant: str,
        category: str,
    ) -> dict[str, Any]:
        """Özel kategori ekler.

        Args:
            merchant: Mağaza adı.
            category: Kategori.

        Returns:
            Ekleme sonucu.
        """
        try:
            low = merchant.lower()
            self._custom[low] = category

            return {
                "merchant": merchant,
                "category": category,
                "total_custom": len(
                    self._custom
                ),
                "added": True,
            }

        except Exception as e:
            logger.error(
                f"Ozel kategori ekleme "
                f"hatasi: {e}"
            )
            return {
                "merchant": merchant,
                "category": category,
                "added": False,
                "error": str(e),
            }

    def map_merchant(
        self,
        merchant: str,
    ) -> dict[str, Any]:
        """Mağaza eşlemesi yapar.

        Args:
            merchant: Mağaza adı.

        Returns:
            Eşleme sonucu.
        """
        try:
            low = merchant.lower()
            if low in self._custom:
                category = self._custom[low]
                source = "custom"
            elif low in self._mappings:
                category = (
                    self._mappings[low]
                )
                source = "default"
            else:
                category = "unknown"
                source = "none"

            return {
                "merchant": merchant,
                "category": category,
                "source": source,
                "mapped": category
                != "unknown",
            }

        except Exception as e:
            logger.error(
                f"Magaza esleme "
                f"hatasi: {e}"
            )
            return {
                "merchant": merchant,
                "category": "unknown",
                "source": "none",
                "mapped": False,
                "error": str(e),
            }

    def learn_pattern(
        self,
        transactions: list[dict[str, Any]]
        | None = None,
    ) -> dict[str, Any]:
        """Harcama örüntüsü öğrenir.

        Args:
            transactions: İşlem listesi.

        Returns:
            Öğrenme sonucu.
        """
        try:
            if transactions is None:
                transactions = []

            patterns: dict[str, int] = {}
            for t in transactions:
                cat = t.get(
                    "category",
                    "uncategorized",
                )
                patterns[cat] = (
                    patterns.get(cat, 0) + 1
                )

            top_category = (
                max(
                    patterns,
                    key=patterns.get,
                )
                if patterns
                else "none"
            )

            return {
                "patterns": patterns,
                "pattern_count": len(
                    patterns
                ),
                "top_category": top_category,
                "transactions_analyzed": len(
                    transactions
                ),
                "learned": True,
            }

        except Exception as e:
            logger.error(
                f"Oruntu ogrenme "
                f"hatasi: {e}"
            )
            return {
                "patterns": {},
                "pattern_count": 0,
                "top_category": "none",
                "transactions_analyzed": 0,
                "learned": False,
                "error": str(e),
            }

    def split_transaction(
        self,
        amount: float = 0.0,
        splits: list[dict[str, Any]]
        | None = None,
    ) -> dict[str, Any]:
        """İşlemi böler.

        Args:
            amount: Toplam tutar.
            splits: Bölme bilgileri.

        Returns:
            Bölme sonucu.
        """
        try:
            if splits is None:
                splits = []

            split_total = sum(
                s.get("amount", 0)
                for s in splits
            )
            remainder = round(
                amount - split_total, 2
            )
            balanced = abs(remainder) < 0.01

            return {
                "original_amount": amount,
                "split_count": len(splits),
                "split_total": round(
                    split_total, 2
                ),
                "remainder": remainder,
                "balanced": balanced,
                "split": True,
            }

        except Exception as e:
            logger.error(
                f"Islem bolme hatasi: {e}"
            )
            return {
                "original_amount": amount,
                "split_count": 0,
                "split_total": 0.0,
                "remainder": amount,
                "balanced": False,
                "split": False,
                "error": str(e),
            }
