"""ATLAS Gorev Zamanlayici modulu.

Cron-like zamanlama, tek seferlik
zamanlama, tekrarlayan gorevler,
oncelik ve son tarih yonetimi.
"""

import logging
import time
from typing import Any

from app.models.scheduler import (
    ScheduleStatus,
    ScheduleType,
    ScheduledTask,
)

logger = logging.getLogger(__name__)


class TaskScheduler:
    """Gorev zamanlayici.

    Gorevlerin zamanlanmasi, onceliklendirilmesi
    ve yasam dongusunu yonetir.

    Attributes:
        _tasks: Zamanlanmis gorevler.
        _history: Calisma gecmisi.
    """

    def __init__(self) -> None:
        """Zamanlayiciyi baslatir."""
        self._tasks: dict[str, ScheduledTask] = {}
        self._history: list[dict[str, Any]] = []
        self._max_concurrent: int = 10
        self._running: set[str] = set()

        logger.info("TaskScheduler baslatildi")

    def schedule_once(
        self,
        name: str,
        run_at: float | None = None,
        priority: int = 5,
    ) -> ScheduledTask:
        """Tek seferlik gorev zamanlar.

        Args:
            name: Gorev adi.
            run_at: Calisma zamani (epoch).
            priority: Oncelik (1-10).

        Returns:
            Zamanlanmis gorev.
        """
        task = ScheduledTask(
            name=name,
            schedule_type=ScheduleType.ONE_TIME,
            status=ScheduleStatus.PENDING,
            priority=max(1, min(10, priority)),
        )
        self._tasks[task.task_id] = task
        logger.info("Tek seferlik gorev: %s", name)
        return task

    def schedule_recurring(
        self,
        name: str,
        interval_seconds: int,
        priority: int = 5,
    ) -> ScheduledTask:
        """Tekrarlayan gorev zamanlar.

        Args:
            name: Gorev adi.
            interval_seconds: Tekrar araligi (saniye).
            priority: Oncelik (1-10).

        Returns:
            Zamanlanmis gorev.
        """
        task = ScheduledTask(
            name=name,
            schedule_type=ScheduleType.RECURRING,
            status=ScheduleStatus.ACTIVE,
            priority=max(1, min(10, priority)),
            interval_seconds=max(1, interval_seconds),
        )
        self._tasks[task.task_id] = task
        logger.info(
            "Tekrarlayan gorev: %s (%ds)",
            name, interval_seconds,
        )
        return task

    def schedule_cron(
        self,
        name: str,
        cron_expr: str,
        priority: int = 5,
    ) -> ScheduledTask:
        """Cron ifadesiyle gorev zamanlar.

        Args:
            name: Gorev adi.
            cron_expr: Cron ifadesi.
            priority: Oncelik (1-10).

        Returns:
            Zamanlanmis gorev.
        """
        task = ScheduledTask(
            name=name,
            schedule_type=ScheduleType.CRON,
            status=ScheduleStatus.ACTIVE,
            priority=max(1, min(10, priority)),
            cron_expr=cron_expr,
        )
        self._tasks[task.task_id] = task
        logger.info("Cron gorev: %s [%s]", name, cron_expr)
        return task

    def pause_task(self, task_id: str) -> bool:
        """Gorevi duraklatir.

        Args:
            task_id: Gorev ID.

        Returns:
            Basarili ise True.
        """
        task = self._tasks.get(task_id)
        if not task:
            return False
        if task.status in (
            ScheduleStatus.COMPLETED,
            ScheduleStatus.CANCELLED,
        ):
            return False
        task.status = ScheduleStatus.PAUSED
        return True

    def resume_task(self, task_id: str) -> bool:
        """Gorevi devam ettirir.

        Args:
            task_id: Gorev ID.

        Returns:
            Basarili ise True.
        """
        task = self._tasks.get(task_id)
        if not task:
            return False
        if task.status != ScheduleStatus.PAUSED:
            return False
        task.status = ScheduleStatus.ACTIVE
        return True

    def cancel_task(self, task_id: str) -> bool:
        """Gorevi iptal eder.

        Args:
            task_id: Gorev ID.

        Returns:
            Basarili ise True.
        """
        task = self._tasks.get(task_id)
        if not task:
            return False
        task.status = ScheduleStatus.CANCELLED
        self._running.discard(task_id)
        return True

    def complete_task(self, task_id: str) -> bool:
        """Gorevi tamamlar.

        Args:
            task_id: Gorev ID.

        Returns:
            Basarili ise True.
        """
        task = self._tasks.get(task_id)
        if not task:
            return False
        task.status = ScheduleStatus.COMPLETED
        self._running.discard(task_id)
        self._history.append({
            "task_id": task_id,
            "name": task.name,
            "completed_at": time.time(),
        })
        return True

    def get_pending(self) -> list[ScheduledTask]:
        """Bekleyen gorevleri getirir.

        Returns:
            Bekleyen gorev listesi.
        """
        pending = [
            t for t in self._tasks.values()
            if t.status in (
                ScheduleStatus.PENDING,
                ScheduleStatus.ACTIVE,
            )
        ]
        return sorted(pending, key=lambda t: t.priority)

    def get_by_priority(
        self,
        min_priority: int = 1,
    ) -> list[ScheduledTask]:
        """Oncelige gore gorevleri getirir.

        Args:
            min_priority: Minimum oncelik.

        Returns:
            Filtrelenmis gorevler.
        """
        return [
            t for t in self._tasks.values()
            if t.priority >= min_priority
            and t.status not in (
                ScheduleStatus.COMPLETED,
                ScheduleStatus.CANCELLED,
            )
        ]

    def get_task(self, task_id: str) -> ScheduledTask | None:
        """Gorevi getirir.

        Args:
            task_id: Gorev ID.

        Returns:
            Gorev veya None.
        """
        return self._tasks.get(task_id)

    @property
    def task_count(self) -> int:
        """Toplam gorev sayisi."""
        return len(self._tasks)

    @property
    def active_count(self) -> int:
        """Aktif gorev sayisi."""
        return sum(
            1 for t in self._tasks.values()
            if t.status in (
                ScheduleStatus.PENDING,
                ScheduleStatus.ACTIVE,
            )
        )

    @property
    def history_count(self) -> int:
        """Gecmis sayisi."""
        return len(self._history)
