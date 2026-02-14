"""ATLAS Program Optimizasyonu modulu.

Program optimizasyonu, bosluk doldurma,
toplu zamanlama, kaynak seviyeleme
ve ne-olursa analizi.
"""

import logging
from typing import Any

from app.models.scheduler import ScheduleStatus

logger = logging.getLogger(__name__)


class ScheduleOptimizer:
    """Program optimizasyonu.

    Programlari optimize eder, bosluklari
    doldurur ve senaryolari analiz eder.

    Attributes:
        _schedule_items: Program ogoleri.
        _optimizations: Uygulanan optimizasyonlar.
        _scenarios: What-if senaryolari.
    """

    def __init__(self) -> None:
        """Program optimizasyonunu baslatir."""
        self._schedule_items: list[dict[str, Any]] = []
        self._optimizations: list[dict[str, Any]] = []
        self._scenarios: list[dict[str, Any]] = []

        logger.info("ScheduleOptimizer baslatildi")

    def add_item(
        self,
        item_id: str,
        start: float,
        duration: float,
        priority: int = 5,
        dependencies: list[str] | None = None,
    ) -> dict[str, Any]:
        """Program ogesi ekler.

        Args:
            item_id: Oge ID.
            start: Baslangic zamani (epoch).
            duration: Sure (saat).
            priority: Oncelik.
            dependencies: Bagimlilklar.

        Returns:
            Oge bilgisi.
        """
        item = {
            "item_id": item_id,
            "start": start,
            "duration": duration,
            "end": start + duration * 3600,
            "priority": priority,
            "dependencies": dependencies or [],
            "status": ScheduleStatus.PENDING.value,
        }
        self._schedule_items.append(item)
        return item

    def find_gaps(
        self,
        min_gap_hours: float = 0.5,
    ) -> list[dict[str, Any]]:
        """Bosluklari bulur.

        Args:
            min_gap_hours: Minimum bosluk suresi.

        Returns:
            Bosluk listesi.
        """
        if len(self._schedule_items) < 2:
            return []

        sorted_items = sorted(
            self._schedule_items, key=lambda x: x["start"],
        )
        gaps: list[dict[str, Any]] = []

        for i in range(len(sorted_items) - 1):
            current_end = sorted_items[i]["end"]
            next_start = sorted_items[i + 1]["start"]
            gap_hours = (next_start - current_end) / 3600

            if gap_hours >= min_gap_hours:
                gaps.append({
                    "start": current_end,
                    "end": next_start,
                    "gap_hours": round(gap_hours, 2),
                })

        return gaps

    def fill_gap(
        self,
        item_id: str,
        gap_index: int,
    ) -> bool:
        """Boslugu doldurur.

        Args:
            item_id: Yerlestirilecek oge ID.
            gap_index: Bosluk indeksi.

        Returns:
            Basarili ise True.
        """
        gaps = self.find_gaps()
        if gap_index >= len(gaps):
            return False

        gap = gaps[gap_index]
        item = {
            "item_id": item_id,
            "start": gap["start"],
            "duration": gap["gap_hours"],
            "end": gap["end"],
            "priority": 5,
            "dependencies": [],
            "status": ScheduleStatus.PENDING.value,
        }
        self._schedule_items.append(item)
        self._optimizations.append({
            "type": "gap_fill",
            "item_id": item_id,
        })
        return True

    def batch_schedule(
        self,
        items: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Toplu zamanlama yapar.

        Args:
            items: Zamanlanacak ogeler.

        Returns:
            Zamanlanmis ogeler.
        """
        sorted_items = sorted(
            items, key=lambda x: x.get("priority", 5),
        )
        scheduled: list[dict[str, Any]] = []
        current_time = max(
            (i["end"] for i in self._schedule_items),
            default=0.0,
        )

        for item in sorted_items:
            duration = item.get("duration", 1.0)
            entry = {
                "item_id": item.get("item_id", ""),
                "start": current_time,
                "duration": duration,
                "end": current_time + duration * 3600,
                "priority": item.get("priority", 5),
                "dependencies": [],
                "status": ScheduleStatus.PENDING.value,
            }
            self._schedule_items.append(entry)
            scheduled.append(entry)
            current_time = entry["end"]

        self._optimizations.append({
            "type": "batch",
            "count": len(scheduled),
        })
        return scheduled

    def level_resources(
        self,
        max_concurrent: int = 3,
    ) -> dict[str, Any]:
        """Kaynak seviyeleme yapar.

        Args:
            max_concurrent: Max esanli gorev.

        Returns:
            Seviyeleme sonucu.
        """
        sorted_items = sorted(
            self._schedule_items, key=lambda x: x["start"],
        )
        adjustments = 0

        for i, item in enumerate(sorted_items):
            concurrent = sum(
                1 for other in sorted_items[:i]
                if other["end"] > item["start"]
                and other["status"] != ScheduleStatus.COMPLETED.value
            )
            if concurrent >= max_concurrent:
                # Ogeyi ertele
                last_end = max(
                    (
                        o["end"] for o in sorted_items[:i]
                        if o["end"] > item["start"]
                    ),
                    default=item["start"],
                )
                item["start"] = last_end
                item["end"] = last_end + item["duration"] * 3600
                adjustments += 1

        self._optimizations.append({
            "type": "level_resources",
            "adjustments": adjustments,
        })
        return {
            "adjustments": adjustments,
            "max_concurrent": max_concurrent,
        }

    def what_if(
        self,
        scenario_name: str,
        changes: dict[str, Any],
    ) -> dict[str, Any]:
        """Ne-olursa analizi yapar.

        Args:
            scenario_name: Senaryo adi.
            changes: Degisiklikler.

        Returns:
            Analiz sonucu.
        """
        total_items = len(self._schedule_items)
        affected = 0

        remove_ids = changes.get("remove", [])
        for item in self._schedule_items:
            if item["item_id"] in remove_ids:
                affected += 1

        add_count = len(changes.get("add", []))
        delay_hours = changes.get("delay_hours", 0)

        if delay_hours > 0:
            affected = total_items

        scenario = {
            "name": scenario_name,
            "total_items": total_items,
            "affected_items": affected,
            "added_items": add_count,
            "removed_items": len(remove_ids),
            "delay_hours": delay_hours,
            "impact": "high" if affected > total_items * 0.5
            else "medium" if affected > 0
            else "low",
        }
        self._scenarios.append(scenario)
        return scenario

    def optimize(self) -> dict[str, Any]:
        """Programi optimize eder.

        Returns:
            Optimizasyon sonucu.
        """
        # Oncelige gore sirala
        self._schedule_items.sort(
            key=lambda x: x["priority"],
        )

        # Bosluklari bul ve bildir
        gaps = self.find_gaps()

        self._optimizations.append({
            "type": "full_optimize",
            "gaps_found": len(gaps),
        })

        return {
            "total_items": len(self._schedule_items),
            "gaps_found": len(gaps),
            "optimizations_applied": len(
                self._optimizations,
            ),
        }

    @property
    def item_count(self) -> int:
        """Oge sayisi."""
        return len(self._schedule_items)

    @property
    def optimization_count(self) -> int:
        """Optimizasyon sayisi."""
        return len(self._optimizations)

    @property
    def scenario_count(self) -> int:
        """Senaryo sayisi."""
        return len(self._scenarios)
