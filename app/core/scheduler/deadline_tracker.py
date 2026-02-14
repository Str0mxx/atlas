"""ATLAS Son Tarih Takipcisi modulu.

Son tarih izleme, uyari esikleri,
gecikme islemleri, oncelik ayarlama
ve uzatma yonetimi.
"""

import logging
import time
from typing import Any

from app.models.scheduler import DeadlinePriority, DeadlineRecord

logger = logging.getLogger(__name__)


class DeadlineTracker:
    """Son tarih takipcisi.

    Son tarihleri izler, uyarilar uretir
    ve gecikmeleri yonetir.

    Attributes:
        _deadlines: Son tarihler.
        _warning_hours: Uyari esigi (saat).
    """

    def __init__(
        self,
        warning_hours: int = 24,
    ) -> None:
        """Son tarih takipcisini baslatir.

        Args:
            warning_hours: Uyari esigi (saat).
        """
        self._deadlines: dict[str, DeadlineRecord] = {}
        self._warning_hours = max(1, warning_hours)
        self._extensions_log: list[dict[str, Any]] = []

        logger.info("DeadlineTracker baslatildi")

    def add_deadline(
        self,
        task_name: str,
        due_at: float,
        priority: DeadlinePriority = DeadlinePriority.MEDIUM,
    ) -> DeadlineRecord:
        """Son tarih ekler.

        Args:
            task_name: Gorev adi.
            due_at: Son tarih (epoch).
            priority: Oncelik.

        Returns:
            Son tarih kaydi.
        """
        from datetime import datetime, timezone

        record = DeadlineRecord(
            task_name=task_name,
            due_at=datetime.fromtimestamp(
                due_at, tz=timezone.utc,
            ),
            priority=priority,
        )
        self._deadlines[record.deadline_id] = record
        logger.info("Son tarih eklendi: %s", task_name)
        return record

    def check_deadlines(
        self,
        current_time: float | None = None,
    ) -> dict[str, Any]:
        """Son tarihleri kontrol eder.

        Args:
            current_time: Mevcut zaman (epoch).

        Returns:
            Kontrol sonucu.
        """
        now = current_time or time.time()
        warning_sec = self._warning_hours * 3600

        overdue: list[str] = []
        warning: list[str] = []
        on_track: list[str] = []

        for dl in self._deadlines.values():
            if dl.completed:
                continue
            due_epoch = dl.due_at.timestamp()
            remaining = due_epoch - now

            if remaining < 0:
                dl.overdue = True
                overdue.append(dl.deadline_id)
            elif remaining < warning_sec:
                warning.append(dl.deadline_id)
            else:
                on_track.append(dl.deadline_id)

        return {
            "overdue": overdue,
            "warning": warning,
            "on_track": on_track,
        }

    def complete_deadline(
        self,
        deadline_id: str,
    ) -> bool:
        """Son tarihi tamamlar.

        Args:
            deadline_id: Son tarih ID.

        Returns:
            Basarili ise True.
        """
        dl = self._deadlines.get(deadline_id)
        if not dl:
            return False
        dl.completed = True
        dl.overdue = False
        return True

    def extend_deadline(
        self,
        deadline_id: str,
        extra_hours: int,
    ) -> bool:
        """Son tarihi uzatir.

        Args:
            deadline_id: Son tarih ID.
            extra_hours: Ekstra saat.

        Returns:
            Basarili ise True.
        """
        from datetime import timedelta

        dl = self._deadlines.get(deadline_id)
        if not dl:
            return False
        if dl.completed:
            return False

        dl.due_at = dl.due_at + timedelta(hours=extra_hours)
        dl.extensions += 1
        dl.overdue = False

        self._extensions_log.append({
            "deadline_id": deadline_id,
            "extra_hours": extra_hours,
            "new_due_at": dl.due_at.isoformat(),
        })
        return True

    def adjust_priority(
        self,
        deadline_id: str,
        new_priority: DeadlinePriority,
    ) -> bool:
        """Oncelik ayarlar.

        Args:
            deadline_id: Son tarih ID.
            new_priority: Yeni oncelik.

        Returns:
            Basarili ise True.
        """
        dl = self._deadlines.get(deadline_id)
        if not dl:
            return False
        dl.priority = new_priority
        return True

    def get_overdue(self) -> list[DeadlineRecord]:
        """Gecikenleri getirir.

        Returns:
            Geciken son tarihler.
        """
        return [
            dl for dl in self._deadlines.values()
            if dl.overdue and not dl.completed
        ]

    def get_by_priority(
        self,
        priority: DeadlinePriority,
    ) -> list[DeadlineRecord]:
        """Oncelige gore getirir.

        Args:
            priority: Oncelik filtresi.

        Returns:
            Filtrelenmis son tarihler.
        """
        return [
            dl for dl in self._deadlines.values()
            if dl.priority == priority
            and not dl.completed
        ]

    def get_deadline(
        self,
        deadline_id: str,
    ) -> DeadlineRecord | None:
        """Son tarih getirir.

        Args:
            deadline_id: Son tarih ID.

        Returns:
            Son tarih veya None.
        """
        return self._deadlines.get(deadline_id)

    @property
    def deadline_count(self) -> int:
        """Son tarih sayisi."""
        return len(self._deadlines)

    @property
    def overdue_count(self) -> int:
        """Geciken sayisi."""
        return sum(
            1 for dl in self._deadlines.values()
            if dl.overdue and not dl.completed
        )

    @property
    def extension_count(self) -> int:
        """Uzatma sayisi."""
        return len(self._extensions_log)
