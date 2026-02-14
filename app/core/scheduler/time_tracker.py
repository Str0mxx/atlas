"""ATLAS Zaman Takipcisi modulu.

Zaman kaydi, aktivite takibi,
uretkenlik metrikleri, rapor uretimi
ve faturalama entegrasyonu.
"""

import logging
import time
from typing import Any

from app.models.scheduler import TimeEntryType

logger = logging.getLogger(__name__)


class TimeTracker:
    """Zaman takipcisi.

    Zaman harcamalarini takip eder
    ve raporlar uretir.

    Attributes:
        _entries: Zaman girisleri.
        _active_timer: Aktif zamanlayici.
        _billing_rates: Faturalama oranlari.
    """

    def __init__(self) -> None:
        """Zaman takipcisini baslatir."""
        self._entries: list[dict[str, Any]] = []
        self._active_timer: dict[str, Any] | None = None
        self._billing_rates: dict[str, float] = {}
        self._categories: dict[str, float] = {}

        logger.info("TimeTracker baslatildi")

    def start_timer(
        self,
        task_id: str,
        entry_type: TimeEntryType = TimeEntryType.WORK,
    ) -> dict[str, Any]:
        """Zamanlayici baslatir.

        Args:
            task_id: Gorev ID.
            entry_type: Giris turu.

        Returns:
            Zamanlayici bilgisi.
        """
        if self._active_timer:
            self.stop_timer()

        self._active_timer = {
            "task_id": task_id,
            "type": entry_type.value,
            "start": time.time(),
        }
        return self._active_timer.copy()

    def stop_timer(self) -> dict[str, Any] | None:
        """Zamanlayiciyi durdurur.

        Returns:
            Tamamlanan giris veya None.
        """
        if not self._active_timer:
            return None

        entry = self._active_timer.copy()
        entry["end"] = time.time()
        entry["duration_hours"] = round(
            (entry["end"] - entry["start"]) / 3600, 4,
        )

        self._entries.append(entry)

        # Kategori toplami guncelle
        cat = entry["type"]
        self._categories[cat] = (
            self._categories.get(cat, 0.0)
            + entry["duration_hours"]
        )

        self._active_timer = None
        return entry

    def log_time(
        self,
        task_id: str,
        hours: float,
        entry_type: TimeEntryType = TimeEntryType.WORK,
    ) -> dict[str, Any]:
        """Manuel zaman kaydeder.

        Args:
            task_id: Gorev ID.
            hours: Saat.
            entry_type: Giris turu.

        Returns:
            Giris bilgisi.
        """
        entry = {
            "task_id": task_id,
            "type": entry_type.value,
            "duration_hours": hours,
            "manual": True,
        }
        self._entries.append(entry)

        cat = entry_type.value
        self._categories[cat] = (
            self._categories.get(cat, 0.0) + hours
        )
        return entry

    def set_billing_rate(
        self,
        category: str,
        rate_per_hour: float,
    ) -> None:
        """Faturalama orani ayarlar.

        Args:
            category: Kategori.
            rate_per_hour: Saatlik ucret.
        """
        self._billing_rates[category] = rate_per_hour

    def calculate_billing(
        self,
        task_id: str | None = None,
    ) -> dict[str, Any]:
        """Faturalama hesaplar.

        Args:
            task_id: Gorev filtresi (opsiyonel).

        Returns:
            Faturalama bilgisi.
        """
        total_hours = 0.0
        total_cost = 0.0

        for entry in self._entries:
            if task_id and entry["task_id"] != task_id:
                continue
            hours = entry.get("duration_hours", 0.0)
            total_hours += hours
            rate = self._billing_rates.get(
                entry["type"], 0.0,
            )
            total_cost += hours * rate

        return {
            "task_id": task_id,
            "total_hours": round(total_hours, 2),
            "total_cost": round(total_cost, 2),
        }

    def get_productivity_metrics(self) -> dict[str, Any]:
        """Uretkenlik metrikleri getirir.

        Returns:
            Metrikler.
        """
        work_hours = self._categories.get("work", 0.0)
        break_hours = self._categories.get("break", 0.0)
        meeting_hours = self._categories.get("meeting", 0.0)
        total = sum(self._categories.values())

        return {
            "total_hours": round(total, 2),
            "work_hours": round(work_hours, 2),
            "break_hours": round(break_hours, 2),
            "meeting_hours": round(meeting_hours, 2),
            "work_ratio": round(
                work_hours / total, 2,
            ) if total > 0 else 0.0,
            "entry_count": len(self._entries),
        }

    def get_report(
        self,
        group_by: str = "type",
    ) -> dict[str, Any]:
        """Rapor uretir.

        Args:
            group_by: Gruplama alani.

        Returns:
            Rapor.
        """
        if group_by == "type":
            return {
                "group_by": "type",
                "breakdown": dict(self._categories),
                "total_entries": len(self._entries),
            }

        # task_id ile gruplama
        by_task: dict[str, float] = {}
        for entry in self._entries:
            tid = entry["task_id"]
            by_task[tid] = (
                by_task.get(tid, 0.0)
                + entry.get("duration_hours", 0.0)
            )

        return {
            "group_by": "task",
            "breakdown": by_task,
            "total_entries": len(self._entries),
        }

    @property
    def entry_count(self) -> int:
        """Giris sayisi."""
        return len(self._entries)

    @property
    def total_hours(self) -> float:
        """Toplam saat."""
        return round(
            sum(self._categories.values()), 2,
        )

    @property
    def is_tracking(self) -> bool:
        """Aktif zamanlayici var mi."""
        return self._active_timer is not None
