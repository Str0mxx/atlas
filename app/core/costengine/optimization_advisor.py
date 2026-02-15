"""ATLAS Maliyet Optimizasyon Danismani modulu.

Maliyet azaltma ipuclari, verimlilik onerileri,
israf tespiti, toplu firsatlar, cache onerileri.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class CostOptimizationAdvisor:
    """Maliyet optimizasyon danismani.

    Maliyet optimizasyonu onerir.

    Attributes:
        _suggestions: Oneri kayitlari.
        _patterns: Harcama kaliplari.
    """

    def __init__(self) -> None:
        """Optimizasyon danismanini baslatir."""
        self._suggestions: list[
            dict[str, Any]
        ] = []
        self._patterns: dict[
            str, dict[str, Any]
        ] = {}
        self._applied: list[
            dict[str, Any]
        ] = []
        self._stats = {
            "suggested": 0,
            "applied": 0,
            "total_savings": 0.0,
        }

        logger.info(
            "CostOptimizationAdvisor baslatildi",
        )

    def analyze_spending(
        self,
        costs: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Harcama analizi yapar.

        Args:
            costs: Maliyet kayitlari.

        Returns:
            Analiz sonucu.
        """
        if not costs:
            return {
                "suggestions": [],
                "potential_savings": 0.0,
            }

        total = sum(
            c.get("amount", 0) for c in costs
        )
        by_category: dict[str, float] = {}
        for c in costs:
            cat = c.get("category", "other")
            by_category[cat] = (
                by_category.get(cat, 0.0)
                + c.get("amount", 0)
            )

        suggestions = []

        # En pahali kategori
        if by_category:
            top_cat = max(
                by_category,
                key=by_category.get,
            )
            top_pct = (
                by_category[top_cat] / total * 100
                if total > 0
                else 0
            )
            if top_pct > 50:
                suggestions.append({
                    "type": "concentration",
                    "category": top_cat,
                    "pct": round(top_pct, 1),
                    "suggestion": (
                        f"Reduce {top_cat} costs"
                        f" ({top_pct:.0f}% of total)"
                    ),
                    "estimated_savings": round(
                        by_category[top_cat] * 0.1,
                        4,
                    ),
                })

        # Tekrar eden maliyetler
        services: dict[str, int] = {}
        for c in costs:
            svc = c.get(
                "service",
                c.get("description", ""),
            )
            if svc:
                services[svc] = (
                    services.get(svc, 0) + 1
                )

        for svc, count in services.items():
            if count > 5:
                suggestions.append({
                    "type": "caching",
                    "service": svc,
                    "calls": count,
                    "suggestion": (
                        f"Cache {svc} results"
                        f" ({count} calls)"
                    ),
                    "estimated_savings": round(
                        count * 0.005, 4,
                    ),
                })

        potential = sum(
            s.get("estimated_savings", 0)
            for s in suggestions
        )

        self._suggestions.extend(suggestions)
        self._stats["suggested"] += len(
            suggestions,
        )

        return {
            "total_spent": round(total, 4),
            "by_category": by_category,
            "suggestions": suggestions,
            "potential_savings": round(
                potential, 4,
            ),
        }

    def suggest_caching(
        self,
        service: str,
        call_count: int,
        cost_per_call: float,
        cache_hit_rate: float = 0.7,
    ) -> dict[str, Any]:
        """Cache onerisi verir.

        Args:
            service: Servis adi.
            call_count: Cagri sayisi.
            cost_per_call: Cagri basina maliyet.
            cache_hit_rate: Cache hit orani.

        Returns:
            Oneri bilgisi.
        """
        current_cost = call_count * cost_per_call
        cached_calls = int(
            call_count * cache_hit_rate
        )
        remaining_calls = call_count - cached_calls
        new_cost = remaining_calls * cost_per_call
        savings = current_cost - new_cost

        suggestion = {
            "type": "caching",
            "service": service,
            "current_cost": round(
                current_cost, 4,
            ),
            "estimated_cost": round(new_cost, 4),
            "savings": round(savings, 4),
            "savings_pct": round(
                cache_hit_rate * 100, 1,
            ),
            "timestamp": time.time(),
        }

        self._suggestions.append(suggestion)
        self._stats["suggested"] += 1

        return suggestion

    def suggest_batching(
        self,
        operations: int,
        cost_per_op: float,
        batch_size: int = 10,
        batch_discount: float = 0.3,
    ) -> dict[str, Any]:
        """Batch onerisi verir.

        Args:
            operations: Islem sayisi.
            cost_per_op: Islem basina maliyet.
            batch_size: Batch boyutu.
            batch_discount: Batch indirimi.

        Returns:
            Oneri bilgisi.
        """
        current_cost = operations * cost_per_op
        batches = (
            (operations + batch_size - 1)
            // batch_size
        )
        batch_cost_per_op = (
            cost_per_op * (1 - batch_discount)
        )
        new_cost = operations * batch_cost_per_op
        savings = current_cost - new_cost

        suggestion = {
            "type": "batching",
            "operations": operations,
            "batch_size": batch_size,
            "current_cost": round(
                current_cost, 4,
            ),
            "estimated_cost": round(new_cost, 4),
            "savings": round(savings, 4),
            "batches": batches,
            "timestamp": time.time(),
        }

        self._suggestions.append(suggestion)
        self._stats["suggested"] += 1

        return suggestion

    def detect_waste(
        self,
        costs: list[dict[str, Any]],
        threshold: float = 0.01,
    ) -> dict[str, Any]:
        """Israf tespit eder.

        Args:
            costs: Maliyet kayitlari.
            threshold: Min israf esigi.

        Returns:
            Israf bilgisi.
        """
        waste = []
        total_waste = 0.0

        # Dusuk degerli yuksek maliyetli islemler
        for c in costs:
            amount = c.get("amount", 0)
            benefit = c.get("benefit", 0)
            if amount > threshold and benefit == 0:
                waste.append({
                    "cost": c,
                    "reason": "no_benefit",
                    "amount": amount,
                })
                total_waste += amount

        # Tekrar eden islemler
        seen: dict[str, list] = {}
        for c in costs:
            key = (
                f"{c.get('category', '')}_"
                f"{c.get('description', '')}"
            )
            if key not in seen:
                seen[key] = []
            seen[key].append(c)

        for key, items in seen.items():
            if len(items) > 3:
                dup_cost = sum(
                    i.get("amount", 0)
                    for i in items[1:]
                )
                if dup_cost > threshold:
                    waste.append({
                        "reason": "duplicate",
                        "key": key,
                        "count": len(items),
                        "amount": round(
                            dup_cost, 4,
                        ),
                    })
                    total_waste += dup_cost

        return {
            "waste_items": len(waste),
            "total_waste": round(total_waste, 4),
            "details": waste,
        }

    def apply_suggestion(
        self,
        suggestion_index: int,
    ) -> dict[str, Any]:
        """Oneri uygular.

        Args:
            suggestion_index: Oneri indeksi.

        Returns:
            Uygulama bilgisi.
        """
        if suggestion_index >= len(
            self._suggestions,
        ):
            return {"error": "invalid_index"}

        suggestion = self._suggestions[
            suggestion_index
        ]
        savings = suggestion.get(
            "estimated_savings",
            suggestion.get("savings", 0),
        )

        self._applied.append({
            "suggestion": suggestion,
            "applied_at": time.time(),
        })
        self._stats["applied"] += 1
        self._stats["total_savings"] += savings

        return {
            "applied": True,
            "savings": round(savings, 4),
            "type": suggestion.get("type"),
        }

    def get_suggestions(
        self,
        suggestion_type: str | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """Onerileri getirir.

        Args:
            suggestion_type: Tip filtresi.
            limit: Limit.

        Returns:
            Oneri listesi.
        """
        suggestions = self._suggestions
        if suggestion_type:
            suggestions = [
                s for s in suggestions
                if s.get("type") == suggestion_type
            ]
        return list(suggestions[-limit:])

    @property
    def suggestion_count(self) -> int:
        """Oneri sayisi."""
        return len(self._suggestions)

    @property
    def total_savings(self) -> float:
        """Toplam tasarruf."""
        return round(
            self._stats["total_savings"], 4,
        )
