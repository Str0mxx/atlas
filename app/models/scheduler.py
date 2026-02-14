"""Time & Schedule Management veri modelleri."""

from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class ScheduleType(str, Enum):
    """Zamanlama turu."""

    ONE_TIME = "one_time"
    RECURRING = "recurring"
    CRON = "cron"
    INTERVAL = "interval"


class ScheduleStatus(str, Enum):
    """Zamanlama durumu."""

    PENDING = "pending"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    OVERDUE = "overdue"


class ReminderChannel(str, Enum):
    """Hatirlatma kanali."""

    TELEGRAM = "telegram"
    EMAIL = "email"
    WEBHOOK = "webhook"
    LOG = "log"


class DeadlinePriority(str, Enum):
    """Son tarih onceligi."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class WorkloadStatus(str, Enum):
    """Is yuku durumu."""

    IDLE = "idle"
    LIGHT = "light"
    NORMAL = "normal"
    HEAVY = "heavy"
    OVERLOADED = "overloaded"


class TimeEntryType(str, Enum):
    """Zaman girisi turu."""

    WORK = "work"
    BREAK = "break"
    MEETING = "meeting"
    PLANNING = "planning"
    REVIEW = "review"


class ScheduledTask(BaseModel):
    """Zamanlanmis gorev."""

    task_id: str = Field(
        default_factory=lambda: str(uuid4())[:8],
    )
    name: str = ""
    schedule_type: ScheduleType = ScheduleType.ONE_TIME
    status: ScheduleStatus = ScheduleStatus.PENDING
    priority: int = 5
    cron_expr: str = ""
    interval_seconds: int = 0
    next_run: datetime | None = None
    last_run: datetime | None = None
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
    )


class CalendarEvent(BaseModel):
    """Takvim olayi."""

    event_id: str = Field(
        default_factory=lambda: str(uuid4())[:8],
    )
    title: str = ""
    start_time: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
    )
    end_time: datetime | None = None
    timezone: str = "UTC"
    recurring: bool = False
    tags: list[str] = Field(default_factory=list)


class ReminderRecord(BaseModel):
    """Hatirlatma kaydi."""

    reminder_id: str = Field(
        default_factory=lambda: str(uuid4())[:8],
    )
    message: str = ""
    channel: ReminderChannel = ReminderChannel.LOG
    due_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
    )
    sent: bool = False
    snoozed: int = 0
    completed: bool = False


class DeadlineRecord(BaseModel):
    """Son tarih kaydi."""

    deadline_id: str = Field(
        default_factory=lambda: str(uuid4())[:8],
    )
    task_name: str = ""
    due_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
    )
    priority: DeadlinePriority = DeadlinePriority.MEDIUM
    completed: bool = False
    overdue: bool = False
    extensions: int = 0


class SchedulerSnapshot(BaseModel):
    """Zamanlayici goruntusu."""

    total_tasks: int = 0
    active_tasks: int = 0
    pending_reminders: int = 0
    overdue_deadlines: int = 0
    events_today: int = 0
    workload_status: WorkloadStatus = WorkloadStatus.NORMAL
    tracked_hours: float = 0.0
    optimizations: int = 0
