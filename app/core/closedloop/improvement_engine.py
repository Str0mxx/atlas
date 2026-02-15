"""ATLAS Iyilestirme Motoru modulu.

Iyilestirme tespiti, degisiklik onceliklendirme,
ogrenme uygulama, etki olcme, yineleme.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class ImprovementEngine:
    """Iyilestirme motoru.

    Ogrenimlerden iyilestirme cikarir ve uygular.

    Attributes:
        _improvements: Iyilestirme kayitlari.
        _applied: Uygulanan iyilestirmeler.
    """

    def __init__(
        self,
        auto_apply: bool = False,
    ) -> None:
        """Iyilestirme motorunu baslatir.

        Args:
            auto_apply: Otomatik uygulama.
        """
        self._improvements: dict[
            str, dict[str, Any]
        ] = {}
        self._applied: list[
            dict[str, Any]
        ] = []
        self._impact_records: dict[
            str, dict[str, Any]
        ] = {}
        self._iteration_history: list[
            dict[str, Any]
        ] = []
        self._auto_apply = auto_apply
        self._stats = {
            "identified": 0,
            "applied": 0,
            "measured": 0,
            "iterations": 0,
        }

        logger.info(
            "ImprovementEngine baslatildi",
        )

    def identify_improvement(
        self,
        improvement_id: str,
        description: str,
        source_action: str = "",
        priority: str = "medium",
        expected_impact: float = 0.5,
    ) -> dict[str, Any]:
        """Iyilestirme tespit eder.

        Args:
            improvement_id: Iyilestirme ID.
            description: Aciklama.
            source_action: Kaynak aksiyon.
            priority: Oncelik.
            expected_impact: Beklenen etki.

        Returns:
            Tespit bilgisi.
        """
        priority_order = {
            "critical": 0,
            "high": 1,
            "medium": 2,
            "low": 3,
            "trivial": 4,
        }

        improvement = {
            "improvement_id": improvement_id,
            "description": description,
            "source_action": source_action,
            "priority": priority,
            "priority_order": priority_order.get(
                priority, 2,
            ),
            "expected_impact": expected_impact,
            "status": "identified",
            "created_at": time.time(),
            "applied_at": None,
        }

        self._improvements[improvement_id] = (
            improvement
        )
        self._stats["identified"] += 1

        # Otomatik uygulama
        if self._auto_apply and priority in (
            "critical", "high",
        ):
            self.apply_improvement(improvement_id)

        return {
            "improvement_id": improvement_id,
            "priority": priority,
            "status": improvement["status"],
            "identified": True,
        }

    def prioritize(
        self,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """Iyilestirmeleri onceliklendirir.

        Args:
            limit: Limit.

        Returns:
            Oncelikli iyilestirme listesi.
        """
        pending = [
            imp
            for imp in self._improvements.values()
            if imp["status"] == "identified"
        ]

        # Oncelik sirasi + beklenen etki
        pending.sort(
            key=lambda x: (
                x["priority_order"],
                -x["expected_impact"],
            ),
        )

        return [
            {
                "improvement_id": imp[
                    "improvement_id"
                ],
                "description": imp["description"],
                "priority": imp["priority"],
                "expected_impact": imp[
                    "expected_impact"
                ],
            }
            for imp in pending[:limit]
        ]

    def apply_improvement(
        self,
        improvement_id: str,
    ) -> dict[str, Any]:
        """Iyilestirmeyi uygular.

        Args:
            improvement_id: Iyilestirme ID.

        Returns:
            Uygulama bilgisi.
        """
        imp = self._improvements.get(
            improvement_id,
        )
        if not imp:
            return {"error": "improvement_not_found"}

        if imp["status"] == "applied":
            return {"error": "already_applied"}

        imp["status"] = "applied"
        imp["applied_at"] = time.time()

        self._applied.append({
            "improvement_id": improvement_id,
            "applied_at": imp["applied_at"],
        })
        self._stats["applied"] += 1

        return {
            "improvement_id": improvement_id,
            "status": "applied",
            "applied": True,
        }

    def measure_impact(
        self,
        improvement_id: str,
        before_metric: float,
        after_metric: float,
    ) -> dict[str, Any]:
        """Etki olcer.

        Args:
            improvement_id: Iyilestirme ID.
            before_metric: Onceki metrik.
            after_metric: Sonraki metrik.

        Returns:
            Etki bilgisi.
        """
        imp = self._improvements.get(
            improvement_id,
        )
        if not imp:
            return {"error": "improvement_not_found"}

        if before_metric == 0:
            change_pct = (
                100.0
                if after_metric != 0
                else 0.0
            )
        else:
            change_pct = (
                (after_metric - before_metric)
                / abs(before_metric)
                * 100
            )

        positive = after_metric > before_metric

        impact = {
            "improvement_id": improvement_id,
            "before": before_metric,
            "after": after_metric,
            "change_pct": round(change_pct, 1),
            "positive": positive,
            "measured_at": time.time(),
        }

        self._impact_records[improvement_id] = (
            impact
        )
        self._stats["measured"] += 1

        return {
            "improvement_id": improvement_id,
            "change_pct": impact["change_pct"],
            "positive": positive,
            "measured": True,
        }

    def iterate(
        self,
        cycle_name: str = "",
    ) -> dict[str, Any]:
        """Yineleme yapar.

        Args:
            cycle_name: Dongu adi.

        Returns:
            Yineleme bilgisi.
        """
        # Mevcut durum ozeti
        total = self._stats["identified"]
        applied = self._stats["applied"]
        measured = self._stats["measured"]

        # Pozitif etki orani
        positive_impacts = sum(
            1
            for imp in self._impact_records.values()
            if imp.get("positive")
        )
        impact_rate = (
            positive_impacts / measured
            if measured > 0
            else 0.0
        )

        iteration = {
            "cycle_name": cycle_name or (
                f"iter_{self._stats['iterations'] + 1}"
            ),
            "total_improvements": total,
            "applied": applied,
            "measured": measured,
            "positive_impact_rate": round(
                impact_rate, 3,
            ),
            "timestamp": time.time(),
        }

        self._iteration_history.append(iteration)
        self._stats["iterations"] += 1

        return {
            "cycle_name": iteration["cycle_name"],
            "positive_impact_rate": iteration[
                "positive_impact_rate"
            ],
            "iteration": self._stats["iterations"],
        }

    def get_improvement(
        self,
        improvement_id: str,
    ) -> dict[str, Any] | None:
        """Iyilestirmeyi getirir.

        Args:
            improvement_id: Iyilestirme ID.

        Returns:
            Iyilestirme verisi veya None.
        """
        imp = self._improvements.get(
            improvement_id,
        )
        if imp:
            return dict(imp)
        return None

    def get_impact(
        self,
        improvement_id: str,
    ) -> dict[str, Any] | None:
        """Etkiyi getirir.

        Args:
            improvement_id: Iyilestirme ID.

        Returns:
            Etki verisi veya None.
        """
        return self._impact_records.get(
            improvement_id,
        )

    def get_iteration_history(
        self,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """Yineleme gecmisini getirir.

        Args:
            limit: Limit.

        Returns:
            Gecmis kayitlari.
        """
        return list(
            self._iteration_history[-limit:],
        )

    @property
    def improvement_count(self) -> int:
        """Iyilestirme sayisi."""
        return len(self._improvements)

    @property
    def applied_count(self) -> int:
        """Uygulanan sayisi."""
        return len(self._applied)

    @property
    def impact_count(self) -> int:
        """Etki olcumu sayisi."""
        return len(self._impact_records)
