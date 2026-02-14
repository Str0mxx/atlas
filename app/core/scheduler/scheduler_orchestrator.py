"""ATLAS Zamanlama Orkestratoru modulu.

Tam zamanlama pipeline, tum alt
sistemlerle entegrasyon, bildirim
yonetimi, analitik ve kullanici
tercihleri.
"""

import logging
import time
from typing import Any

from app.models.scheduler import (
    DeadlinePriority,
    ReminderChannel,
    SchedulerSnapshot,
    TimeEntryType,
    WorkloadStatus,
)

from app.core.scheduler.calendar_manager import CalendarManager
from app.core.scheduler.deadline_tracker import DeadlineTracker
from app.core.scheduler.reminder_system import ReminderSystem
from app.core.scheduler.schedule_optimizer import ScheduleOptimizer
from app.core.scheduler.task_scheduler import TaskScheduler
from app.core.scheduler.time_estimator import TimeEstimator
from app.core.scheduler.time_tracker import TimeTracker
from app.core.scheduler.workload_balancer import WorkloadBalancer

logger = logging.getLogger(__name__)


class SchedulerOrchestrator:
    """Zamanlama orkestratoru.

    Tum zamanlama alt sistemlerini
    koordine eder ve birlesik arayuz saglar.

    Attributes:
        scheduler: Gorev zamanlayici.
        calendar: Takvim yoneticisi.
        reminders: Hatirlatma sistemi.
        deadlines: Son tarih takipcisi.
        estimator: Sure tahmincisi.
        workload: Is yuku dengeleyici.
        tracker: Zaman takipcisi.
        optimizer: Program optimizasyonu.
    """

    def __init__(
        self,
        workday_start: str = "09:00",
        workday_end: str = "18:00",
        default_reminder_minutes: int = 15,
        deadline_warning_hours: int = 24,
    ) -> None:
        """Orkestratoru baslatir.

        Args:
            workday_start: Is gunu baslangici.
            workday_end: Is gunu bitisi.
            default_reminder_minutes: Varsayilan hatirlatma.
            deadline_warning_hours: Son tarih uyari esigi.
        """
        self.scheduler = TaskScheduler()
        self.calendar = CalendarManager(
            workday_start=workday_start,
            workday_end=workday_end,
        )
        self.reminders = ReminderSystem(
            default_minutes=default_reminder_minutes,
        )
        self.deadlines = DeadlineTracker(
            warning_hours=deadline_warning_hours,
        )
        self.estimator = TimeEstimator()
        self.workload = WorkloadBalancer()
        self.tracker = TimeTracker()
        self.optimizer = ScheduleOptimizer()

        self._preferences: dict[str, Any] = {}
        self._notifications: list[dict[str, Any]] = []
        self._start_time = time.time()

        logger.info("SchedulerOrchestrator baslatildi")

    def schedule_task(
        self,
        name: str,
        deadline_epoch: float | None = None,
        priority: int = 5,
        estimated_hours: float = 1.0,
        category: str = "general",
    ) -> dict[str, Any]:
        """Gorev zamanlar (tam pipeline).

        Args:
            name: Gorev adi.
            deadline_epoch: Son tarih (epoch).
            priority: Oncelik (1-10).
            estimated_hours: Tahmini sure.
            category: Kategori.

        Returns:
            Zamanlama sonucu.
        """
        # 1. Gorevi zamanla
        task = self.scheduler.schedule_once(
            name=name, priority=priority,
        )

        # 2. Sure tahmini
        estimate = self.estimator.estimate(
            task_id=task.task_id,
            category=category,
            base_hours=estimated_hours,
        )

        # 3. Son tarih ekle
        deadline = None
        if deadline_epoch:
            dl = self.deadlines.add_deadline(
                task_name=name,
                due_at=deadline_epoch,
                priority=DeadlinePriority.HIGH
                if priority >= 7
                else DeadlinePriority.MEDIUM,
            )
            deadline = dl.deadline_id

        # 4. Hatirlatma olustur
        reminder = self.reminders.create_reminder(
            message=f"Gorev: {name}",
            channel=ReminderChannel.LOG,
        )

        return {
            "task_id": task.task_id,
            "name": name,
            "estimated_hours": estimate["total_hours"],
            "deadline_id": deadline,
            "reminder_id": reminder.reminder_id,
        }

    def complete_task(
        self,
        task_id: str,
        actual_hours: float | None = None,
        category: str = "general",
    ) -> dict[str, Any]:
        """Gorevi tamamlar.

        Args:
            task_id: Gorev ID.
            actual_hours: Gercek sure.
            category: Kategori.

        Returns:
            Tamamlama sonucu.
        """
        self.scheduler.complete_task(task_id)

        comparison = None
        if actual_hours is not None:
            comparison = self.estimator.record_actual(
                task_id=task_id,
                actual_hours=actual_hours,
                category=category,
            )

        return {
            "task_id": task_id,
            "completed": True,
            "comparison": comparison,
        }

    def check_all_deadlines(self) -> dict[str, Any]:
        """Tum son tarihleri kontrol eder.

        Returns:
            Kontrol sonucu.
        """
        result = self.deadlines.check_deadlines()

        # Gecikenlere bildirim
        for dl_id in result.get("overdue", []):
            self._notifications.append({
                "type": "deadline_overdue",
                "deadline_id": dl_id,
                "time": time.time(),
            })

        # Uyari esigindekiler
        for dl_id in result.get("warning", []):
            self._notifications.append({
                "type": "deadline_warning",
                "deadline_id": dl_id,
                "time": time.time(),
            })

        return result

    def get_analytics(self) -> dict[str, Any]:
        """Analitik verileri getirir.

        Returns:
            Analitik.
        """
        productivity = self.tracker.get_productivity_metrics()
        accuracy = self.estimator.get_accuracy_stats()
        load_dist = self.workload.get_load_distribution()

        return {
            "productivity": productivity,
            "estimation_accuracy": accuracy,
            "workload_distribution": load_dist,
            "total_scheduled": self.scheduler.task_count,
            "active_tasks": self.scheduler.active_count,
            "pending_reminders": self.reminders.pending_count,
            "overdue_deadlines": self.deadlines.overdue_count,
            "notifications": len(self._notifications),
        }

    def set_preference(
        self,
        key: str,
        value: Any,
    ) -> None:
        """Kullanici tercihi ayarlar.

        Args:
            key: Tercih anahtari.
            value: Deger.
        """
        self._preferences[key] = value

    def get_preference(
        self,
        key: str,
        default: Any = None,
    ) -> Any:
        """Kullanici tercihi getirir.

        Args:
            key: Tercih anahtari.
            default: Varsayilan deger.

        Returns:
            Tercih degeri.
        """
        return self._preferences.get(key, default)

    def get_snapshot(self) -> SchedulerSnapshot:
        """Zamanlayici goruntusu getirir.

        Returns:
            Goruntusu.
        """
        overloaded = self.workload.detect_overloaded()
        wl_status = (
            WorkloadStatus.OVERLOADED if overloaded
            else WorkloadStatus.NORMAL
        )

        return SchedulerSnapshot(
            total_tasks=self.scheduler.task_count,
            active_tasks=self.scheduler.active_count,
            pending_reminders=self.reminders.pending_count,
            overdue_deadlines=self.deadlines.overdue_count,
            events_today=self.calendar.event_count,
            workload_status=wl_status,
            tracked_hours=self.tracker.total_hours,
            optimizations=self.optimizer.optimization_count,
        )

    @property
    def notification_count(self) -> int:
        """Bildirim sayisi."""
        return len(self._notifications)

    @property
    def preference_count(self) -> int:
        """Tercih sayisi."""
        return len(self._preferences)
