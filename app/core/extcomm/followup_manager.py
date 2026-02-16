"""ATLAS Takip Yöneticisi modülü.

Takip zamanlama, hatırlatma sistemi,
eskalasyon kuralları, yanıt takibi,
otomatik takip.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class FollowUpManager:
    """Takip yöneticisi.

    İletişim takiplerini planlar ve yönetir.

    Attributes:
        _followups: Takip kayıtları.
        _rules: Eskalasyon kuralları.
    """

    DEFAULT_FOLLOWUP_DAYS = 3
    MAX_FOLLOWUPS = 5

    def __init__(
        self,
        default_days: int = 3,
        max_followups: int = 5,
    ) -> None:
        """Yöneticiyi başlatır.

        Args:
            default_days: Varsayılan gün.
            max_followups: Maks takip sayısı.
        """
        self._followups: list[
            dict[str, Any]
        ] = []
        self._rules: list[
            dict[str, Any]
        ] = []
        self._reminders: list[
            dict[str, Any]
        ] = []
        self._default_days = default_days
        self._max_followups = max_followups
        self._counter = 0
        self._stats = {
            "followups_created": 0,
            "followups_completed": 0,
            "reminders_sent": 0,
            "escalations": 0,
        }

        logger.info(
            "FollowUpManager baslatildi",
        )

    def schedule_followup(
        self,
        contact_id: str,
        email_id: str,
        days: int | None = None,
        priority: str = "medium",
        note: str = "",
    ) -> dict[str, Any]:
        """Takip planlar.

        Args:
            contact_id: Kişi ID.
            email_id: Email ID.
            days: Gün sayısı.
            priority: Öncelik.
            note: Not.

        Returns:
            Takip bilgisi.
        """
        self._counter += 1
        fid = f"fu_{self._counter}"
        follow_days = (
            days or self._default_days
        )
        follow_at = (
            time.time()
            + follow_days * 86400
        )

        followup = {
            "followup_id": fid,
            "contact_id": contact_id,
            "email_id": email_id,
            "priority": priority,
            "note": note,
            "attempt": 1,
            "status": "pending",
            "follow_at": follow_at,
            "created_at": time.time(),
        }
        self._followups.append(followup)
        self._stats[
            "followups_created"
        ] += 1

        return {
            "followup_id": fid,
            "contact_id": contact_id,
            "days": follow_days,
            "priority": priority,
            "status": "pending",
            "scheduled": True,
        }

    def get_due_followups(
        self,
        limit: int = 20,
    ) -> dict[str, Any]:
        """Vadesi gelen takipleri getirir.

        Args:
            limit: Maks kayıt.

        Returns:
            Takip listesi.
        """
        now = time.time()
        due = [
            f for f in self._followups
            if (
                f["status"] == "pending"
                and f["follow_at"] <= now
            )
        ]

        # Önceliğe göre sırala
        priority_order = {
            "critical": 0,
            "high": 1,
            "medium": 2,
            "low": 3,
        }
        due.sort(
            key=lambda x: priority_order.get(
                x["priority"], 99,
            ),
        )

        return {
            "followups": due[:limit],
            "total_due": len(due),
        }

    def complete_followup(
        self,
        followup_id: str,
        outcome: str = "responded",
    ) -> dict[str, Any]:
        """Takibi tamamlar.

        Args:
            followup_id: Takip ID.
            outcome: Sonuç.

        Returns:
            Tamamlama bilgisi.
        """
        for f in self._followups:
            if (
                f["followup_id"]
                == followup_id
            ):
                f["status"] = "completed"
                f["outcome"] = outcome
                f["completed_at"] = (
                    time.time()
                )
                self._stats[
                    "followups_completed"
                ] += 1
                return {
                    "followup_id": (
                        followup_id
                    ),
                    "status": "completed",
                    "outcome": outcome,
                    "completed": True,
                }

        return {
            "error": "followup_not_found",
        }

    def reschedule(
        self,
        followup_id: str,
        days: int = 3,
    ) -> dict[str, Any]:
        """Takibi yeniden planlar.

        Args:
            followup_id: Takip ID.
            days: Gün sayısı.

        Returns:
            Yeniden planlama bilgisi.
        """
        for f in self._followups:
            if (
                f["followup_id"]
                == followup_id
            ):
                if (
                    f["attempt"]
                    >= self._max_followups
                ):
                    return {
                        "error": (
                            "max_followups_"
                            "reached"
                        ),
                        "max": (
                            self._max_followups
                        ),
                    }

                f["attempt"] += 1
                f["follow_at"] = (
                    time.time()
                    + days * 86400
                )
                f["status"] = "pending"

                return {
                    "followup_id": (
                        followup_id
                    ),
                    "attempt": f["attempt"],
                    "days": days,
                    "rescheduled": True,
                }

        return {
            "error": "followup_not_found",
        }

    def add_escalation_rule(
        self,
        name: str,
        max_attempts: int,
        action: str,
        priority: str = "high",
    ) -> dict[str, Any]:
        """Eskalasyon kuralı ekler.

        Args:
            name: Kural adı.
            max_attempts: Maks deneme.
            action: Aksiyon.
            priority: Öncelik.

        Returns:
            Kural bilgisi.
        """
        rule = {
            "name": name,
            "max_attempts": max_attempts,
            "action": action,
            "priority": priority,
        }
        self._rules.append(rule)

        return {
            "name": name,
            "added": True,
            "total_rules": len(self._rules),
        }

    def check_escalations(
        self,
    ) -> dict[str, Any]:
        """Eskalasyonları kontrol eder.

        Returns:
            Eskalasyon bilgisi.
        """
        escalated = []
        for f in self._followups:
            if f["status"] != "pending":
                continue

            for rule in self._rules:
                if (
                    f["attempt"]
                    >= rule["max_attempts"]
                ):
                    escalated.append({
                        "followup_id": f[
                            "followup_id"
                        ],
                        "contact_id": f[
                            "contact_id"
                        ],
                        "attempts": f[
                            "attempt"
                        ],
                        "action": rule[
                            "action"
                        ],
                        "rule": rule["name"],
                    })
                    self._stats[
                        "escalations"
                    ] += 1

        return {
            "escalated": escalated,
            "count": len(escalated),
        }

    def create_reminder(
        self,
        followup_id: str,
        message: str,
    ) -> dict[str, Any]:
        """Hatırlatma oluşturur.

        Args:
            followup_id: Takip ID.
            message: Mesaj.

        Returns:
            Hatırlatma bilgisi.
        """
        self._counter += 1
        rid = f"rem_{self._counter}"

        reminder = {
            "reminder_id": rid,
            "followup_id": followup_id,
            "message": message,
            "created_at": time.time(),
        }
        self._reminders.append(reminder)
        self._stats["reminders_sent"] += 1

        return {
            "reminder_id": rid,
            "followup_id": followup_id,
            "created": True,
        }

    @property
    def followup_count(self) -> int:
        """Takip sayısı."""
        return self._stats[
            "followups_created"
        ]

    @property
    def pending_count(self) -> int:
        """Bekleyen takip sayısı."""
        return sum(
            1 for f in self._followups
            if f["status"] == "pending"
        )
