"""ATLAS Fiyat Karşılaştırıcı modülü.

Çoklu kaynak fiyatlandırma, geçmiş fiyatlar,
trend analizi, en iyi teklif tespiti,
düşüş uyarısı.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class PriceComparator:
    """Fiyat karşılaştırıcı.

    Ürün fiyatlarını karşılaştırır.

    Attributes:
        _prices: Fiyat kayıtları.
        _history: Geçmiş fiyatlar.
    """

    def __init__(self) -> None:
        """Karşılaştırıcıyı başlatır."""
        self._prices: dict[
            str, list[dict[str, Any]]
        ] = {}
        self._history: dict[
            str, list[dict[str, Any]]
        ] = {}
        self._alerts: list[
            dict[str, Any]
        ] = []
        self._counter = 0
        self._stats = {
            "comparisons_done": 0,
            "best_deals_found": 0,
            "alerts_sent": 0,
        }

        logger.info(
            "PriceComparator baslatildi",
        )

    def add_price(
        self,
        item: str,
        supplier: str,
        price: float,
        currency: str = "USD",
    ) -> dict[str, Any]:
        """Fiyat ekler.

        Args:
            item: Ürün.
            supplier: Tedarikçi.
            price: Fiyat.
            currency: Para birimi.

        Returns:
            Ekleme bilgisi.
        """
        self._counter += 1
        pid = f"price_{self._counter}"

        entry = {
            "price_id": pid,
            "item": item,
            "supplier": supplier,
            "price": price,
            "currency": currency,
            "timestamp": time.time(),
        }

        if item not in self._prices:
            self._prices[item] = []
        self._prices[item].append(entry)

        if item not in self._history:
            self._history[item] = []
        self._history[item].append({
            "price": price,
            "supplier": supplier,
            "timestamp": time.time(),
        })

        return {
            "price_id": pid,
            "item": item,
            "supplier": supplier,
            "price": price,
            "added": True,
        }

    def compare_prices(
        self,
        item: str,
    ) -> dict[str, Any]:
        """Fiyat karşılaştırır.

        Args:
            item: Ürün.

        Returns:
            Karşılaştırma bilgisi.
        """
        prices = self._prices.get(item, [])

        if not prices:
            return {
                "item": item,
                "compared": False,
                "reason": "No prices found",
            }

        sorted_prices = sorted(
            prices,
            key=lambda x: x["price"],
        )
        cheapest = sorted_prices[0]
        most_exp = sorted_prices[-1]

        spread = round(
            most_exp["price"]
            - cheapest["price"], 2,
        )

        self._stats[
            "comparisons_done"
        ] += 1

        return {
            "item": item,
            "cheapest": cheapest[
                "supplier"
            ],
            "cheapest_price": cheapest[
                "price"
            ],
            "most_expensive": most_exp[
                "supplier"
            ],
            "highest_price": most_exp[
                "price"
            ],
            "spread": spread,
            "source_count": len(prices),
            "compared": True,
        }

    def get_historical(
        self,
        item: str,
        limit: int = 10,
    ) -> dict[str, Any]:
        """Geçmiş fiyatları döndürür.

        Args:
            item: Ürün.
            limit: Limit.

        Returns:
            Geçmiş bilgisi.
        """
        history = self._history.get(
            item, [],
        )[-limit:]

        if not history:
            return {
                "item": item,
                "entries": [],
                "count": 0,
            }

        prices = [
            h["price"] for h in history
        ]
        avg = round(
            sum(prices) / len(prices), 2,
        )

        return {
            "item": item,
            "entries": history,
            "count": len(history),
            "avg_price": avg,
            "min_price": min(prices),
            "max_price": max(prices),
        }

    def analyze_trend(
        self,
        item: str,
    ) -> dict[str, Any]:
        """Trend analizi yapar.

        Args:
            item: Ürün.

        Returns:
            Trend bilgisi.
        """
        history = self._history.get(
            item, [],
        )

        if len(history) < 2:
            return {
                "item": item,
                "trend": "insufficient_data",
            }

        prices = [
            h["price"] for h in history
        ]
        first_half = prices[
            :len(prices) // 2
        ]
        second_half = prices[
            len(prices) // 2:
        ]

        avg_first = (
            sum(first_half) / len(first_half)
        )
        avg_second = (
            sum(second_half)
            / len(second_half)
        )

        if avg_second > avg_first * 1.05:
            trend = "increasing"
        elif avg_second < avg_first * 0.95:
            trend = "decreasing"
        else:
            trend = "stable"

        change_pct = round(
            (avg_second - avg_first)
            / max(avg_first, 0.01) * 100, 1,
        )

        return {
            "item": item,
            "trend": trend,
            "change_pct": change_pct,
            "data_points": len(prices),
        }

    def find_best_deal(
        self,
        item: str,
    ) -> dict[str, Any]:
        """En iyi teklifi bulur.

        Args:
            item: Ürün.

        Returns:
            Teklif bilgisi.
        """
        prices = self._prices.get(item, [])

        if not prices:
            return {
                "item": item,
                "found": False,
            }

        best = min(
            prices,
            key=lambda x: x["price"],
        )

        avg = sum(
            p["price"] for p in prices
        ) / len(prices)
        savings_pct = round(
            (avg - best["price"])
            / max(avg, 0.01) * 100, 1,
        )

        self._stats[
            "best_deals_found"
        ] += 1

        return {
            "item": item,
            "supplier": best["supplier"],
            "price": best["price"],
            "avg_price": round(avg, 2),
            "savings_pct": savings_pct,
            "found": True,
        }

    def alert_on_drop(
        self,
        item: str,
        threshold_pct: float = 10.0,
    ) -> dict[str, Any]:
        """Düşüş uyarısı verir.

        Args:
            item: Ürün.
            threshold_pct: Eşik yüzdesi.

        Returns:
            Uyarı bilgisi.
        """
        history = self._history.get(
            item, [],
        )

        if len(history) < 2:
            return {
                "item": item,
                "alert": False,
            }

        prev = history[-2]["price"]
        current = history[-1]["price"]
        drop_pct = round(
            (prev - current)
            / max(prev, 0.01) * 100, 1,
        )

        alert = drop_pct >= threshold_pct

        if alert:
            self._alerts.append({
                "item": item,
                "drop_pct": drop_pct,
                "timestamp": time.time(),
            })
            self._stats[
                "alerts_sent"
            ] += 1

        return {
            "item": item,
            "previous_price": prev,
            "current_price": current,
            "drop_pct": drop_pct,
            "threshold": threshold_pct,
            "alert": alert,
        }

    @property
    def comparison_count(self) -> int:
        """Karşılaştırma sayısı."""
        return self._stats[
            "comparisons_done"
        ]

    @property
    def deal_count(self) -> int:
        """Teklif sayısı."""
        return self._stats[
            "best_deals_found"
        ]
