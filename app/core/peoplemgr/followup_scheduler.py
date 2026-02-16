"""ATLAS Takip Zamanlayıcı modülü.

Takip zamanlama, optimal zamanlama,
hatırlatma sistemi, önceliklendirme,
otomatik zamanlama.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class PeopleFollowUpScheduler:
    """Takip zamanlayıcı.

    Kişi takiplerini zamanlar.

    Attributes:
        _followups: Takip kayıtları.
        _reminders: Hatırlatma kayıtları.
    """

    def __init__(self) -> None:
        """Zamanlayıcıyı başlatır."""
        self._followups: dict[
            str, dict[str, Any]
        ] = {}
        self._reminders: list[
            dict[str, Any]
        ] = []
        self._counter = 0
        self._stats = {
            "followups_scheduled": 0,
            "reminders_sent": 0,
            "auto_scheduled": 0,
        }

        logger.info(
            "PeopleFollowUpScheduler "
            "baslatildi",
        )

    def schedule_followup(
        self,
        contact_id: str,
        action: str,
        days_from_now: float = 7.0,
        priority: str = "normal",
        notes: str = "",
    ) -> dict[str, Any]:
        """Takip zamanlar.

        Args:
            contact_id: Kişi ID.
            action: Aksiyon.
            days_from_now: Gün sonra.
            priority: Öncelik.
            notes: Notlar.

        Returns:
            Zamanlama bilgisi.
        """
        self._counter += 1
        fid = f"fu_{self._counter}"

        followup = {
            "followup_id": fid,
            "contact_id": contact_id,
            "action": action,
            "scheduled_at": (
                time.time()
                + days_from_now * 86400
            ),
            "priority": priority,
            "notes": notes,
            "status": "scheduled",
            "created_at": time.time(),
        }
        self._followups[fid] = followup
        self._stats[
            "followups_scheduled"
        ] += 1

        return {
            "followup_id": fid,
            "contact_id": contact_id,
            "action": action,
            "days_from_now": days_from_now,
            "priority": priority,
            "scheduled": True,
        }

    def find_optimal_time(
        self,
        contact_id: str,
        preferred_day: str = "weekday",
        preferred_hour: int = 10,
    ) -> dict[str, Any]:
        """Optimal zaman bulur.

        Args:
            contact_id: Kişi ID.
            preferred_day: Tercih edilen gün.
            preferred_hour: Tercih edilen saat.

        Returns:
            Zaman bilgisi.
        """
        # Basit optimal zaman hesaplaması
        if preferred_day == "weekend":
            days_offset = max(
                5 - int(
                    time.localtime().tm_wday
                ), 0,
            )
        else:
            wday = int(
                time.localtime().tm_wday,
            )
            if wday >= 5:
                days_offset = 7 - wday
            else:
                days_offset = 1

        return {
            "contact_id": contact_id,
            "suggested_day": preferred_day,
            "suggested_hour": (
                preferred_hour
            ),
            "days_offset": days_offset,
            "optimal": True,
        }

    def create_reminder(
        self,
        followup_id: str,
        remind_before_hours: float = 24.0,
        channel: str = "telegram",
    ) -> dict[str, Any]:
        """Hatırlatma oluşturur.

        Args:
            followup_id: Takip ID.
            remind_before_hours: Saat önce.
            channel: Kanal.

        Returns:
            Hatırlatma bilgisi.
        """
        followup = self._followups.get(
            followup_id,
        )
        if not followup:
            return {
                "followup_id": followup_id,
                "reminded": False,
                "reason": "not_found",
            }

        reminder = {
            "followup_id": followup_id,
            "remind_at": (
                followup["scheduled_at"]
                - remind_before_hours * 3600
            ),
            "channel": channel,
            "status": "pending",
        }
        self._reminders.append(reminder)
        self._stats[
            "reminders_sent"
        ] += 1

        return {
            "followup_id": followup_id,
            "channel": channel,
            "remind_before_hours": (
                remind_before_hours
            ),
            "reminded": True,
        }

    def prioritize(
        self,
    ) -> list[dict[str, Any]]:
        """Önceliklendirme yapar.

        Returns:
            Öncelik sırası.
        """
        priority_order = {
            "urgent": 0,
            "high": 1,
            "normal": 2,
            "low": 3,
            "optional": 4,
        }

        pending = [
            f for f in
            self._followups.values()
            if f["status"] == "scheduled"
        ]

        pending.sort(
            key=lambda x: (
                priority_order.get(
                    x["priority"], 2,
                ),
                x["scheduled_at"],
            ),
        )

        return [
            {
                "followup_id": f[
                    "followup_id"
                ],
                "contact_id": f[
                    "contact_id"
                ],
                "action": f["action"],
                "priority": f["priority"],
            }
            for f in pending
        ]

    def auto_schedule(
        self,
        contact_id: str,
        relationship_score: float = 50.0,
        last_contact_days: float = 30.0,
    ) -> dict[str, Any]:
        """Otomatik zamanlar.

        Args:
            contact_id: Kişi ID.
            relationship_score: İlişki puanı.
            last_contact_days: Son temas.

        Returns:
            Zamanlama bilgisi.
        """
        # Puana göre temas sıklığı
        if relationship_score >= 80:
            interval = 7
        elif relationship_score >= 60:
            interval = 14
        elif relationship_score >= 40:
            interval = 30
        else:
            interval = 60

        # Gecikme varsa acilleştir
        overdue = (
            last_contact_days > interval
        )
        if overdue:
            days_from_now = 1.0
            priority = "high"
        else:
            days_from_now = max(
                interval
                - last_contact_days, 1,
            )
            priority = "normal"

        result = self.schedule_followup(
            contact_id=contact_id,
            action="auto_followup",
            days_from_now=days_from_now,
            priority=priority,
        )
        self._stats[
            "auto_scheduled"
        ] += 1

        result["overdue"] = overdue
        result["interval_days"] = interval
        return result

    def complete_followup(
        self,
        followup_id: str,
    ) -> dict[str, Any]:
        """Takibi tamamlar.

        Args:
            followup_id: Takip ID.

        Returns:
            Tamamlama bilgisi.
        """
        followup = self._followups.get(
            followup_id,
        )
        if not followup:
            return {
                "followup_id": followup_id,
                "completed": False,
            }

        followup["status"] = "completed"
        followup[
            "completed_at"
        ] = time.time()

        return {
            "followup_id": followup_id,
            "completed": True,
        }

    def get_pending(
        self,
        contact_id: str = "",
    ) -> list[dict[str, Any]]:
        """Bekleyen takipleri listeler."""
        results = [
            f for f in
            self._followups.values()
            if f["status"] == "scheduled"
        ]
        if contact_id:
            results = [
                f for f in results
                if f["contact_id"]
                == contact_id
            ]
        return results

    @property
    def followup_count(self) -> int:
        """Takip sayısı."""
        return self._stats[
            "followups_scheduled"
        ]

    @property
    def pending_count(self) -> int:
        """Bekleyen sayısı."""
        return sum(
            1 for f in
            self._followups.values()
            if f["status"] == "scheduled"
        )
