"""ATLAS Maliyet Takipcisi modulu.

Gercek zamanli takip, maliyet atfi,
kumulatif maliyetler, gecmis, trend analizi.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class DecisionCostTracker:
    """Karar maliyet takipcisi.

    Karar basina maliyetleri izler.

    Attributes:
        _decisions: Karar kayitlari.
        _costs: Maliyet kayitlari.
    """

    def __init__(self) -> None:
        """Maliyet takipcisini baslatir."""
        self._decisions: dict[
            str, dict[str, Any]
        ] = {}
        self._costs: list[
            dict[str, Any]
        ] = []
        self._by_system: dict[
            str, float
        ] = {}
        self._by_category: dict[
            str, float
        ] = {}
        self._stats = {
            "tracked": 0,
            "total_cost": 0.0,
        }

        logger.info(
            "DecisionCostTracker baslatildi",
        )

    def start_tracking(
        self,
        decision_id: str,
        system: str = "",
        description: str = "",
    ) -> dict[str, Any]:
        """Maliyet takibi baslatir.

        Args:
            decision_id: Karar ID.
            system: Sistem adi.
            description: Aciklama.

        Returns:
            Takip bilgisi.
        """
        self._decisions[decision_id] = {
            "decision_id": decision_id,
            "system": system,
            "description": description,
            "costs": [],
            "total_cost": 0.0,
            "started_at": time.time(),
            "completed_at": None,
        }

        return {
            "decision_id": decision_id,
            "tracking": True,
        }

    def add_cost(
        self,
        decision_id: str,
        category: str,
        amount: float,
        description: str = "",
    ) -> dict[str, Any]:
        """Maliyet ekler.

        Args:
            decision_id: Karar ID.
            category: Kategori.
            amount: Miktar.
            description: Aciklama.

        Returns:
            Ekleme bilgisi.
        """
        decision = self._decisions.get(
            decision_id,
        )
        if not decision:
            return {
                "error": "decision_not_found",
            }

        cost_entry = {
            "decision_id": decision_id,
            "category": category,
            "amount": amount,
            "description": description,
            "timestamp": time.time(),
        }

        decision["costs"].append(cost_entry)
        decision["total_cost"] += amount

        self._costs.append(cost_entry)
        self._stats["tracked"] += 1
        self._stats["total_cost"] += amount

        # Sistem bazli
        system = decision.get("system", "other")
        self._by_system[system] = (
            self._by_system.get(system, 0.0)
            + amount
        )

        # Kategori bazli
        self._by_category[category] = (
            self._by_category.get(category, 0.0)
            + amount
        )

        return {
            "decision_id": decision_id,
            "amount": amount,
            "cumulative": round(
                decision["total_cost"], 6,
            ),
            "added": True,
        }

    def complete_tracking(
        self,
        decision_id: str,
    ) -> dict[str, Any]:
        """Takibi tamamlar.

        Args:
            decision_id: Karar ID.

        Returns:
            Tamamlama bilgisi.
        """
        decision = self._decisions.get(
            decision_id,
        )
        if not decision:
            return {
                "error": "decision_not_found",
            }

        decision["completed_at"] = time.time()
        duration = (
            decision["completed_at"]
            - decision["started_at"]
        )

        return {
            "decision_id": decision_id,
            "total_cost": round(
                decision["total_cost"], 6,
            ),
            "cost_items": len(decision["costs"]),
            "duration_seconds": round(
                duration, 2,
            ),
            "completed": True,
        }

    def get_decision_cost(
        self,
        decision_id: str,
    ) -> dict[str, Any]:
        """Karar maliyetini getirir.

        Args:
            decision_id: Karar ID.

        Returns:
            Maliyet bilgisi.
        """
        decision = self._decisions.get(
            decision_id,
        )
        if not decision:
            return {
                "error": "decision_not_found",
            }

        by_cat: dict[str, float] = {}
        for c in decision["costs"]:
            cat = c["category"]
            by_cat[cat] = (
                by_cat.get(cat, 0.0)
                + c["amount"]
            )

        return {
            "decision_id": decision_id,
            "total_cost": round(
                decision["total_cost"], 6,
            ),
            "by_category": by_cat,
            "cost_items": len(decision["costs"]),
            "system": decision["system"],
        }

    def get_cost_by_system(
        self,
    ) -> dict[str, float]:
        """Sistem bazli maliyetler.

        Returns:
            Sistem-maliyet haritasi.
        """
        return {
            k: round(v, 6)
            for k, v in self._by_system.items()
        }

    def get_cost_by_category(
        self,
    ) -> dict[str, float]:
        """Kategori bazli maliyetler.

        Returns:
            Kategori-maliyet haritasi.
        """
        return {
            k: round(v, 6)
            for k, v in self._by_category.items()
        }

    def get_avg_cost(
        self,
    ) -> float:
        """Ortalama karar maliyeti.

        Returns:
            Ortalama maliyet.
        """
        completed = [
            d for d in self._decisions.values()
            if d["completed_at"] is not None
        ]
        if not completed:
            return 0.0

        total = sum(
            d["total_cost"] for d in completed
        )
        return round(total / len(completed), 6)

    def get_trend(
        self,
        last_n: int = 10,
    ) -> dict[str, Any]:
        """Maliyet trendini analiz eder.

        Args:
            last_n: Son N karar.

        Returns:
            Trend bilgisi.
        """
        completed = [
            d for d in self._decisions.values()
            if d["completed_at"] is not None
        ]
        completed.sort(
            key=lambda x: x["started_at"],
        )
        recent = completed[-last_n:]

        if len(recent) < 2:
            return {
                "direction": "insufficient",
                "count": len(recent),
            }

        mid = len(recent) // 2
        first_half = recent[:mid]
        second_half = recent[mid:]

        first_avg = sum(
            d["total_cost"] for d in first_half
        ) / len(first_half)
        second_avg = sum(
            d["total_cost"] for d in second_half
        ) / len(second_half)

        if first_avg == 0:
            change_pct = (
                100.0 if second_avg > 0 else 0.0
            )
        else:
            change_pct = (
                (second_avg - first_avg)
                / first_avg * 100
            )

        if change_pct > 10:
            direction = "increasing"
        elif change_pct < -10:
            direction = "decreasing"
        else:
            direction = "stable"

        return {
            "direction": direction,
            "change_pct": round(change_pct, 2),
            "first_avg": round(first_avg, 6),
            "second_avg": round(second_avg, 6),
            "count": len(recent),
        }

    def get_history(
        self,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Maliyet gecmisini getirir.

        Args:
            limit: Limit.

        Returns:
            Gecmis kayitlari.
        """
        return list(self._costs[-limit:])

    @property
    def decision_count(self) -> int:
        """Karar sayisi."""
        return len(self._decisions)

    @property
    def total_cost(self) -> float:
        """Toplam maliyet."""
        return round(
            self._stats["total_cost"], 6,
        )
