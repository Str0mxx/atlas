"""ATLAS Yedekleme Zamanlayici modulu.

Zamanlanmis yedeklemeler, saklama politikalari,
yedekleme pencereleri, oncelik yonetimi
ve takvim entegrasyonu.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class BackupScheduler:
    """Yedekleme zamanlayici.

    Yedekleme zamanlamalarini yonetir.

    Attributes:
        _schedules: Zamanlamalar.
        _retention_policies: Saklama politikalari.
    """

    def __init__(self) -> None:
        """Zamanlayiciyi baslatir."""
        self._schedules: dict[
            str, dict[str, Any]
        ] = {}
        self._retention_policies: dict[
            str, dict[str, Any]
        ] = {}
        self._windows: dict[
            str, dict[str, Any]
        ] = {}
        self._calendar: list[
            dict[str, Any]
        ] = []
        self._stats = {
            "scheduled": 0,
            "executed": 0,
            "skipped": 0,
        }

        logger.info(
            "BackupScheduler baslatildi",
        )

    def add_schedule(
        self,
        schedule_id: str,
        backup_type: str = "full",
        cron: str = "0 2 * * *",
        target: str = "",
        priority: int = 5,
        enabled: bool = True,
    ) -> dict[str, Any]:
        """Zamanlama ekler.

        Args:
            schedule_id: Zamanlama ID.
            backup_type: Yedekleme tipi.
            cron: Cron ifadesi.
            target: Hedef.
            priority: Oncelik (1-10).
            enabled: Etkin mi.

        Returns:
            Zamanlama bilgisi.
        """
        self._schedules[schedule_id] = {
            "backup_type": backup_type,
            "cron": cron,
            "target": target,
            "priority": min(max(priority, 1), 10),
            "enabled": enabled,
            "created_at": time.time(),
            "last_run": None,
            "next_run": None,
        }

        self._stats["scheduled"] += 1

        return {
            "schedule_id": schedule_id,
            "status": "created",
        }

    def remove_schedule(
        self,
        schedule_id: str,
    ) -> bool:
        """Zamanlama kaldirir.

        Args:
            schedule_id: Zamanlama ID.

        Returns:
            Basarili mi.
        """
        if schedule_id in self._schedules:
            del self._schedules[schedule_id]
            return True
        return False

    def enable_schedule(
        self,
        schedule_id: str,
    ) -> bool:
        """Zamanlamayi etkinlestirir.

        Args:
            schedule_id: Zamanlama ID.

        Returns:
            Basarili mi.
        """
        sched = self._schedules.get(schedule_id)
        if not sched:
            return False
        sched["enabled"] = True
        return True

    def disable_schedule(
        self,
        schedule_id: str,
    ) -> bool:
        """Zamanlamayi devre disi birakir.

        Args:
            schedule_id: Zamanlama ID.

        Returns:
            Basarili mi.
        """
        sched = self._schedules.get(schedule_id)
        if not sched:
            return False
        sched["enabled"] = False
        return True

    def get_schedule(
        self,
        schedule_id: str,
    ) -> dict[str, Any] | None:
        """Zamanlama getirir.

        Args:
            schedule_id: Zamanlama ID.

        Returns:
            Zamanlama bilgisi veya None.
        """
        return self._schedules.get(schedule_id)

    def set_retention_policy(
        self,
        policy_name: str,
        daily: int = 7,
        weekly: int = 4,
        monthly: int = 12,
        yearly: int = 1,
    ) -> dict[str, Any]:
        """Saklama politikasi ayarlar.

        Args:
            policy_name: Politika adi.
            daily: Gunluk saklama.
            weekly: Haftalik saklama.
            monthly: Aylik saklama.
            yearly: Yillik saklama.

        Returns:
            Politika bilgisi.
        """
        self._retention_policies[policy_name] = {
            "daily": daily,
            "weekly": weekly,
            "monthly": monthly,
            "yearly": yearly,
        }

        return {
            "policy": policy_name,
            "total_kept": (
                daily + weekly + monthly + yearly
            ),
        }

    def get_retention_policy(
        self,
        policy_name: str,
    ) -> dict[str, Any] | None:
        """Saklama politikasi getirir.

        Args:
            policy_name: Politika adi.

        Returns:
            Politika bilgisi veya None.
        """
        return self._retention_policies.get(
            policy_name,
        )

    def set_backup_window(
        self,
        window_id: str,
        start_hour: int = 2,
        end_hour: int = 6,
        days: list[str] | None = None,
    ) -> dict[str, Any]:
        """Yedekleme penceresi ayarlar.

        Args:
            window_id: Pencere ID.
            start_hour: Baslangic saati.
            end_hour: Bitis saati.
            days: Gunler.

        Returns:
            Pencere bilgisi.
        """
        self._windows[window_id] = {
            "start_hour": start_hour,
            "end_hour": end_hour,
            "days": days or [
                "mon", "tue", "wed",
                "thu", "fri", "sat", "sun",
            ],
        }

        return {
            "window_id": window_id,
            "hours": f"{start_hour}-{end_hour}",
        }

    def is_in_window(
        self,
        window_id: str,
        hour: int,
        day: str = "",
    ) -> bool:
        """Pencere icinde mi kontrol eder.

        Args:
            window_id: Pencere ID.
            hour: Saat.
            day: Gun.

        Returns:
            Pencere icinde mi.
        """
        window = self._windows.get(window_id)
        if not window:
            return True

        if day and day not in window["days"]:
            return False

        start = window["start_hour"]
        end = window["end_hour"]

        if start <= end:
            return start <= hour < end
        return hour >= start or hour < end

    def get_due_schedules(
        self,
        current_hour: int = 0,
    ) -> list[dict[str, Any]]:
        """Zamani gelen zamanlamalari getirir.

        Args:
            current_hour: Mevcut saat.

        Returns:
            Zamanlanmis is listesi.
        """
        due: list[dict[str, Any]] = []

        for sid, sched in self._schedules.items():
            if not sched["enabled"]:
                continue

            due.append({
                "schedule_id": sid,
                "backup_type": sched["backup_type"],
                "target": sched["target"],
                "priority": sched["priority"],
            })

        due.sort(
            key=lambda x: x["priority"],
            reverse=True,
        )

        return due

    def mark_executed(
        self,
        schedule_id: str,
    ) -> bool:
        """Zamanlama calistirildi olarak isaretle.

        Args:
            schedule_id: Zamanlama ID.

        Returns:
            Basarili mi.
        """
        sched = self._schedules.get(schedule_id)
        if not sched:
            return False

        sched["last_run"] = time.time()
        self._stats["executed"] += 1
        return True

    def add_calendar_event(
        self,
        event_type: str,
        scheduled_at: float,
        description: str = "",
    ) -> dict[str, Any]:
        """Takvim olayi ekler.

        Args:
            event_type: Olay tipi.
            scheduled_at: Zamanlama.
            description: Aciklama.

        Returns:
            Olay bilgisi.
        """
        event = {
            "type": event_type,
            "scheduled_at": scheduled_at,
            "description": description,
        }
        self._calendar.append(event)
        return event

    def list_schedules(
        self,
        enabled_only: bool = False,
    ) -> list[dict[str, Any]]:
        """Zamanlamalari listeler.

        Args:
            enabled_only: Sadece etkin olanlar.

        Returns:
            Zamanlama listesi.
        """
        result = []
        for sid, sched in self._schedules.items():
            if enabled_only and not sched["enabled"]:
                continue
            result.append({
                "schedule_id": sid,
                **sched,
            })
        return result

    @property
    def schedule_count(self) -> int:
        """Zamanlama sayisi."""
        return len(self._schedules)

    @property
    def retention_policy_count(self) -> int:
        """Saklama politikasi sayisi."""
        return len(self._retention_policies)

    @property
    def window_count(self) -> int:
        """Pencere sayisi."""
        return len(self._windows)

    @property
    def calendar_count(self) -> int:
        """Takvim olayi sayisi."""
        return len(self._calendar)
