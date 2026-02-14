"""ATLAS Hatirlatma Sistemi modulu.

Hatirlatma olusturma, cok kanalli
teslim, erteleme, eskalasyon ve
tamamlama takibi.
"""

import logging
import time
from typing import Any

from app.models.scheduler import ReminderChannel, ReminderRecord

logger = logging.getLogger(__name__)


class ReminderSystem:
    """Hatirlatma sistemi.

    Hatirlatmalari yonetir, teslim eder
    ve takip eder.

    Attributes:
        _reminders: Hatirlatmalar.
        _default_minutes: Varsayilan dakika.
        _escalation_rules: Eskalasyon kurallari.
    """

    def __init__(
        self,
        default_minutes: int = 15,
    ) -> None:
        """Hatirlatma sistemini baslatir.

        Args:
            default_minutes: Varsayilan hatirlatma suresi.
        """
        self._reminders: dict[str, ReminderRecord] = {}
        self._default_minutes = max(1, default_minutes)
        self._escalation_rules: list[dict[str, Any]] = []
        self._delivery_log: list[dict[str, Any]] = []

        logger.info("ReminderSystem baslatildi")

    def create_reminder(
        self,
        message: str,
        channel: ReminderChannel = ReminderChannel.LOG,
        due_at: float | None = None,
    ) -> ReminderRecord:
        """Hatirlatma olusturur.

        Args:
            message: Hatirlatma mesaji.
            channel: Teslim kanali.
            due_at: Vade zamani (epoch).

        Returns:
            Hatirlatma kaydi.
        """
        from datetime import datetime, timezone

        dt = (
            datetime.fromtimestamp(due_at, tz=timezone.utc)
            if due_at
            else datetime.now(timezone.utc)
        )
        reminder = ReminderRecord(
            message=message,
            channel=channel,
            due_at=dt,
        )
        self._reminders[reminder.reminder_id] = reminder
        logger.info("Hatirlatma olusturuldu: %s", message)
        return reminder

    def send_reminder(
        self,
        reminder_id: str,
    ) -> bool:
        """Hatirlatmayi gonderir.

        Args:
            reminder_id: Hatirlatma ID.

        Returns:
            Basarili ise True.
        """
        reminder = self._reminders.get(reminder_id)
        if not reminder:
            return False
        if reminder.sent:
            return False

        reminder.sent = True
        self._delivery_log.append({
            "reminder_id": reminder_id,
            "channel": reminder.channel.value,
            "sent_at": time.time(),
        })
        logger.info(
            "Hatirlatma gonderildi: %s [%s]",
            reminder.message, reminder.channel.value,
        )
        return True

    def snooze_reminder(
        self,
        reminder_id: str,
        minutes: int = 0,
    ) -> bool:
        """Hatirlatmayi erteler.

        Args:
            reminder_id: Hatirlatma ID.
            minutes: Erteleme suresi.

        Returns:
            Basarili ise True.
        """
        reminder = self._reminders.get(reminder_id)
        if not reminder:
            return False
        if reminder.completed:
            return False

        snooze_min = minutes or self._default_minutes
        reminder.snoozed += 1
        reminder.sent = False
        logger.info(
            "Hatirlatma ertelendi: %s (%d dk)",
            reminder.message, snooze_min,
        )
        return True

    def complete_reminder(
        self,
        reminder_id: str,
    ) -> bool:
        """Hatirlatmayi tamamlar.

        Args:
            reminder_id: Hatirlatma ID.

        Returns:
            Basarili ise True.
        """
        reminder = self._reminders.get(reminder_id)
        if not reminder:
            return False
        reminder.completed = True
        return True

    def add_escalation_rule(
        self,
        max_snooze: int,
        escalate_to: ReminderChannel,
    ) -> dict[str, Any]:
        """Eskalasyon kurali ekler.

        Args:
            max_snooze: Max erteleme sayisi.
            escalate_to: Eskalasyon kanali.

        Returns:
            Kural bilgisi.
        """
        rule = {
            "max_snooze": max_snooze,
            "escalate_to": escalate_to.value,
        }
        self._escalation_rules.append(rule)
        return rule

    def check_escalation(
        self,
        reminder_id: str,
    ) -> dict[str, Any] | None:
        """Eskalasyon kontrol eder.

        Args:
            reminder_id: Hatirlatma ID.

        Returns:
            Eskalasyon bilgisi veya None.
        """
        reminder = self._reminders.get(reminder_id)
        if not reminder:
            return None

        for rule in self._escalation_rules:
            if reminder.snoozed >= rule["max_snooze"]:
                return {
                    "reminder_id": reminder_id,
                    "snoozed": reminder.snoozed,
                    "escalate_to": rule["escalate_to"],
                }
        return None

    def get_pending(self) -> list[ReminderRecord]:
        """Bekleyen hatirlatmalari getirir.

        Returns:
            Bekleyen hatirlatmalar.
        """
        return [
            r for r in self._reminders.values()
            if not r.completed and not r.sent
        ]

    def get_reminder(
        self,
        reminder_id: str,
    ) -> ReminderRecord | None:
        """Hatirlatma getirir.

        Args:
            reminder_id: Hatirlatma ID.

        Returns:
            Hatirlatma veya None.
        """
        return self._reminders.get(reminder_id)

    @property
    def reminder_count(self) -> int:
        """Hatirlatma sayisi."""
        return len(self._reminders)

    @property
    def pending_count(self) -> int:
        """Bekleyen hatirlatma sayisi."""
        return sum(
            1 for r in self._reminders.values()
            if not r.completed and not r.sent
        )

    @property
    def delivery_count(self) -> int:
        """Teslim sayisi."""
        return len(self._delivery_log)
